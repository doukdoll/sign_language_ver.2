import json
import time
import atexit
from collections import deque
from typing import Optional, Dict, Any, List

import numpy as np
import torch
from flask import Flask, request, jsonify
from flask_sock import Sock
from simple_websocket.errors import ConnectionClosed
from scipy.interpolate import interp1d

# --- 사용자 정의 모듈 임포트 ---
from input_keypoint.advanced_validators import AdvancedHandValidator
from realtime.segmenter import OnlineSegmenter
from realtime.inference_logger import InferenceLogger
from realtime.inference_utils import (
    load_model_and_vocab,
    predict,
    normalize_keypoints_by_bodypart
)
from utils.logger import get_logger, setup_project_logging
from utils.config import load_config, get_default_config_path
from utils.performance import performance_optimizer

# =============================================================================
# [SETUP] 로거 및 설정 초기화
# =============================================================================
setup_project_logging({
    "level": "INFO",
    "log_file": "logs/server.log",
    "format": "[%(asctime)s] %(levelname)s [%(name)s] %(message)s"
})

logger = get_logger("kslt.server")

config_path = get_default_config_path()
config = load_config(config_path)

# =============================================================================
# [CONSTANTS] 상수 정의
# =============================================================================
KEYPOINT_SLICES = {
    'body': slice(0, 25),
    'face': slice(25, 95),
    'left_hand': slice(95, 116),
    'right_hand': slice(116, 137)
}
NOSE_INDEX = 0
INFERENCE_STRIDE = 5

# =============================================================================
# [SERVER INIT] Flask 및 모델 로드
# =============================================================================
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
sock = Sock(app)

MODEL_PATH = "deployment/20251109-1439_Attention/20251109-1439.onnx"
VOCAB_PATH = "deployment/20251109-1439_Attention/vocabulary.txt"
MODEL_TYPE = "onnx"

logger.info("🚀 서버 시작: 모델 및 리소스 로딩 중...")

try:
    SERVICE, VOCAB, DEVICE = load_model_and_vocab(MODEL_PATH, VOCAB_PATH, "auto", MODEL_TYPE)
    realtime_config = config.get_realtime_config()
    logger.info(f"✅ 모델 로드 성공 (Device: {DEVICE}, Type: {MODEL_TYPE})")

except Exception as e:
    logger.critical(f"❌ 치명적 오류: 모델 로드 실패. 서버를 종료해야 합니다. {e}", exc_info=True)
    SERVICE, VOCAB, DEVICE = None, None, None

MAX_BUFFER_FRAMES = realtime_config.get('window_size', 200) if MODEL_TYPE == "onnx" else 180
MIN_BUFFER_FRAMES = MAX_BUFFER_FRAMES // 3
log_interval = realtime_config.get("log_interval", 30)

logger.info(f"⚙️ 설정 완료: Window Size={MAX_BUFFER_FRAMES}, Stride={INFERENCE_STRIDE}, log_interval={log_interval}")

# --- 데이터 로거 설정 ---
data_config = config.get_data_config()
DATA_LOGGER = InferenceLogger(
    win=MAX_BUFFER_FRAMES,
    save_dir=data_config.get('save_dir', "data"),
    prefix="server_inference",
    save_csv_summary=True,
    save_windows_csv=False
)
atexit.register(DATA_LOGGER.save)
logger.info("💾 데이터 로거 활성화됨 (종료 시 'data/' 저장)")

validator_config = realtime_config.get('validator', {})
GLOBAL_VALIDATOR = AdvancedHandValidator(
    head_occlusion_threshold=validator_config.get('head_occlusion_threshold', 0.8),
    min_hand_movement=validator_config.get('min_hand_movement', 0.01),
    max_frame_gap=validator_config.get('max_frame_gap', 10),
    min_valid_frames_ratio=validator_config.get('min_valid_frames_ratio', 0.3)
)


# =============================================================================
# [FUNCTIONS] 핵심 로직
# =============================================================================

def preprocess_frame(keypoints_data: List[List[float]]) -> Optional[np.ndarray]:
    """프론트엔드 데이터를 모델 입력용 1D 벡터로 변환합니다."""
    if not keypoints_data:
        return None

    try:
        keypoints_arr = np.array(keypoints_data, dtype=np.float32)

        if keypoints_arr.shape[1] == 2:
             zeros = np.zeros((keypoints_arr.shape[0], 1), dtype=np.float32)
             keypoints_arr = np.hstack([keypoints_arr, zeros])

        normalized_keypoints = normalize_keypoints_by_bodypart(
            keypoints_arr, width=1.0, height=1.0
        )

        body_pts = normalized_keypoints[KEYPOINT_SLICES['body']]
        face_pts = normalized_keypoints[KEYPOINT_SLICES['face']]
        lh_pts = normalized_keypoints[KEYPOINT_SLICES['left_hand']]
        rh_pts = normalized_keypoints[KEYPOINT_SLICES['right_hand']]

        nose_pt = body_pts[NOSE_INDEX]
        if nose_pt[2] > 0.1 and not np.isnan(nose_pt[0]):
            body_pts[:, :2] -= nose_pt[:2]

        xy = np.concatenate([
            body_pts[:, :2],
            face_pts[:, :2],
            lh_pts[:, :2],
            rh_pts[:, :2]
        ], axis=0)

        presence_mask_list = []
        for part_name in ['body', 'face', 'left_hand', 'right_hand']:
            part_data = xy[KEYPOINT_SLICES[part_name]]
            has_part = not np.all(np.isnan(part_data))
            length = KEYPOINT_SLICES[part_name].stop - KEYPOINT_SLICES[part_name].start
            presence_mask_list.append(np.full((length, 1), 1.0 if has_part else 0.0))

        presence_mask = np.vstack(presence_mask_list).astype(np.float32)
        coord_mask = (~np.isnan(xy).any(axis=1)).astype(np.float32).reshape(-1, 1)
        mask = presence_mask * coord_mask

        xy = np.nan_to_num(xy, nan=0.0, posinf=0.0, neginf=0.0)
        xy *= mask

        return xy.reshape(-1)

    except Exception as e:
        logger.error(f"전처리 중 오류 발생: {e}")
        return None

def resample_and_return_deque(
    frame_buffer: deque[np.ndarray],
    target_frames: int,
) -> deque[np.ndarray]:
    """프레임 보간 함수"""
    if not frame_buffer:
        return frame_buffer

    keypoints_sequence = np.array(frame_buffer)
    original_frames = keypoints_sequence.shape[0]

    if original_frames == target_frames:
        return deque(frame_buffer, maxlen=target_frames)

    original_indices = np.linspace(0, original_frames - 1, original_frames)
    target_indices = np.linspace(0, original_frames - 1, target_frames)

    interpolator = interp1d(original_indices, keypoints_sequence,
                          kind='linear', axis=0,
                          bounds_error=False, fill_value='extrapolate')

    resampled_data = interpolator(target_indices)
    result_deque = deque(resampled_data, maxlen=target_frames)

    return result_deque

def execute_inference(
    frame_buffer: deque,
    service: Any,
    validator: AdvancedHandValidator,
    data_logger: InferenceLogger,
    vocab: Any,
    session_id: str = "unknown",
    top_k: int = 3,
    required_frames: int = 128,
    count_for_log = 0
) -> Optional[Dict[str, Any]]:
    """추론 실행 및 결과 후처리 (천안->서울 로직 포함)"""

    buffer_len = len(frame_buffer)
    if buffer_len == 0:
        return None

    working_buffer = list(frame_buffer)
    if buffer_len < required_frames:
        while len(working_buffer) < required_frames:
            working_buffer.append(working_buffer[-1])

    try:
        start_time = time.perf_counter()
        input_tensor = np.stack(working_buffer[:required_frames], axis=0)

        # 1. 유효성 검증
        keypoints_for_val = input_tensor.reshape(required_frames, 137, 2)
        val_res = validator.validate_sequence(keypoints_for_val, skip_head_occlusion=True)

        if not val_res['is_valid']:
            pass

        # 2. 모델 추론
        result = service.predict(input_tensor, return_probabilities=True, top_k=top_k)
        elapsed = (time.perf_counter() - start_time) * 1000

        prediction = result['top_prediction']
        confidence = float(result['top_confidence'])

        # =========================================================================
        # [RULE OVERRIDE] 천안 -> 서울 보정 로직
        # 조건: 1위가 '천안'이고, 후보군에 '서울'이 10% 초과로 존재할 경우 '서울'로 변경
        # =========================================================================
        is_overridden = False
        if prediction == "천안":
            seoul_entry = next((item for item in result['top_k_predictions'] if item['word'] == "서울"), None)

            if seoul_entry:
                seoul_conf = float(seoul_entry['confidence'])
                if seoul_conf > 10.0:
                    logger.info(f"🔄 [Override] '천안'({confidence:.1f}%) -> '서울'({seoul_conf:.1f}%) 교체됨 (Rule: Seoul > 10%)")
                    prediction = "서울"
                    confidence = seoul_conf
                    is_overridden = True
        # =========================================================================

        # 3. 로깅
        if count_for_log % log_interval == 0 or is_overridden:
            status_tag = "✅ Accepted" if confidence > 60.0 else "⚠️ Low Conf"
            if is_overridden: status_tag += " (Modified)"

            log_msg = (f"[{session_id}] {status_tag} | "
            f"예측: '{prediction}' ({confidence:.1f}%) | "
            f"시간: {elapsed:.1f}ms | 품질: {val_res['quality_score']:.2f}")

            logger.info(log_msg)

            # 원본 Top K 로그 (디버깅용)
            if count_for_log % log_interval == 0:
                logger.info(f"상위 {top_k}개 예측 (원본):")
                for i, pred in enumerate(result['top_k_predictions']):
                    logger.info(f"  {i+1}. {pred['word']}: {pred['confidence']:.1f}%")

        # 4. 데이터 저장
        label_id = -1
        if hasattr(vocab, 'stoi'):
            label_id = vocab.stoi.get(prediction, -1)
        data_logger.add(label_id=label_id, word=prediction, feat_window=input_tensor)

        return {
            "sessionId": session_id,
            "departureCity": prediction,
            "arrivalCity": None,
            "recognizedProb": confidence
        }

    except Exception as e:
        logger.error(f"[{session_id}] 추론 실행 중 오류: {e}", exc_info=True)
        return {"type": "ERROR", "message": str(e)}

# =============================================================================
# [ROUTE] HTTP POST
# =============================================================================
@app.route('/predict_keypoints', methods=['POST'])
def http_predict_keypoints():
    try:
        data = request.get_json()
        session_id = "HTTP_REQ"
        keypoint_input = data.get('keypointData')

        if not keypoint_input:
            return jsonify({"error": "No keypoint data provided"}), 400

        final_keypoints = []
        if isinstance(keypoint_input, dict):
            if 'keypoints' in keypoint_input:
                final_keypoints = keypoint_input['keypoints']
            else:
                body = keypoint_input.get('body') or []
                face = keypoint_input.get('face') or []
                left_hand = keypoint_input.get('leftHand') or []
                right_hand = keypoint_input.get('rightHand') or []
                final_keypoints = body + face + left_hand + right_hand
        elif isinstance(keypoint_input, list):
            final_keypoints = keypoint_input
        else:
            return jsonify({"error": "Unknown data format"}), 400

        if len(final_keypoints) == 0:
            return jsonify({"error": "Extracted keypoints are empty"}), 400

        feature_vector = preprocess_frame(final_keypoints)
        if feature_vector is None:
            return jsonify({"error": "Preprocessing failed"}), 400

        temp_buffer = deque([feature_vector])
        result = execute_inference(
            frame_buffer=temp_buffer,
            service=SERVICE,
            validator=GLOBAL_VALIDATOR,
            data_logger=DATA_LOGGER,
            vocab=VOCAB,
            session_id=session_id,
            required_frames=MAX_BUFFER_FRAMES
        )

        if result and "type" not in result:
            return jsonify(result)
        else:
            return jsonify({"departureCity": "인식 중...", "arrivalCity": None, "recognizedProb": 0.0}), 200

    except Exception as e:
        logger.error(f"HTTP 처리 중 오류: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# =============================================================================
# [ROUTE] WebSocket
# =============================================================================
@sock.route('/ws/predict')
def websocket_predict(ws):
    logger.info("🔗 새로운 WebSocket 클라이언트 연결됨")
    frame_buffer = deque(maxlen=MAX_BUFFER_FRAMES)
    last_frame_index = -1
    session_id = "unknown"
    frames_since_last_inference = 0

    while True:
        try:
            try:
                message_str = ws.receive()
            except ConnectionClosed:
                logger.info(f"[{session_id}] 클라이언트가 연결을 정상 종료했습니다. (Code 1000)")
                break

            if message_str is None:
                logger.info(f"[{session_id}] 클라이언트 연결 종료 (EOF)")
                break

            try:
                message = json.loads(message_str)
            except json.JSONDecodeError:
                logger.warning(f"[{session_id}] 잘못된 JSON 형식 수신")
                continue

            msg_type = message.get('type')

            if msg_type == 'START_SESSION':
                session_id = message.get('sessionId', 'unknown')
                logger.info(f"✨ 세션 시작 [{session_id}] - 버퍼 초기화됨")
                frame_buffer.clear()
                frames_since_last_inference = 0
                ws.send(json.dumps({"status": "connected", "sessionId": session_id}))

            elif msg_type == 'KEYPOINT_FRAME':
                current_index = message.get('frameIndex', -1)
                if current_index >= 0 and current_index < last_frame_index:
                     logger.info(f"[{session_id}] 🔄 클라이언트 재시작 감지")
                     frame_buffer.clear()
                     frames_since_last_inference = 0
                last_frame_index = current_index

                keypoints_data = message.get('keypoints')
                feature_vector = preprocess_frame(keypoints_data)

                if feature_vector is not None:
                    frame_buffer.append(feature_vector)
                    frames_since_last_inference += 1

                    if current_index == MIN_BUFFER_FRAMES:
                        logger.debug("보간 수행 (Initial Buffer Fill)")
                        frame_buffer = resample_and_return_deque(frame_buffer, MAX_BUFFER_FRAMES)

                    if len(frame_buffer) == MAX_BUFFER_FRAMES and \
                       frames_since_last_inference % INFERENCE_STRIDE == 0:

                        result = execute_inference(
                            frame_buffer=frame_buffer,
                            service=SERVICE,
                            validator=GLOBAL_VALIDATOR,
                            data_logger=DATA_LOGGER,
                            vocab=VOCAB,
                            session_id=session_id,
                            required_frames=MAX_BUFFER_FRAMES,
                            count_for_log=frames_since_last_inference
                        )

                        if result:
                            if "type" in result and result["type"] == "ERROR":
                                logger.error(f"[{session_id}] 추론 에러: {result['message']}")
                            else:
                                ws.send(json.dumps(result))

        except Exception as e:
            logger.error(f"WS Error: {e}")
            break

    logger.info(f"👋 연결 완전 종료: {session_id}")

if __name__ == '__main__':
    logger.info("🚀 Flask 앱 실행 중 (Port: 5001)...")
    app.run(host='0.0.0.0', port=5001, debug=False)