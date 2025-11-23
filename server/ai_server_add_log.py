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

# --- 사용자 정의 모듈 임포트 ---
from input_keypoint.advanced_validators import AdvancedHandValidator
from realtime.segmenter import OnlineSegmenter
from realtime.inference_logger import InferenceLogger  # [추가] 데이터 로거
from realtime.inference_utils import (
    load_model_and_vocab,
    predict,
    normalize_keypoints_by_bodypart
)
from utils.logger import get_logger, setup_project_logging # [추가] 로깅 설정
from utils.config import load_config, get_default_config_path
from utils.performance import performance_optimizer

# =============================================================================
# [SETUP] 로거 및 설정 초기화
# =============================================================================
# 1. 로깅 시스템 초기화 (화면 출력 + 파일 저장)
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
# [FUNCTIONS] 핵심 로직
# =============================================================================

def preprocess_frame(keypoints_data: List[List[float]]) -> Optional[np.ndarray]:
    """
    프론트엔드 데이터를 모델 입력용 1D 벡터로 변환합니다.
    """
    if not keypoints_data:
        return None

    try:
        keypoints_arr = np.array(keypoints_data, dtype=np.float32)

        # 데이터 형상 맞추기 (x, y) -> (x, y, 0) 처리 등
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


def execute_inference(
    frame_buffer: deque,
    service: Any,
    validator: AdvancedHandValidator,
    data_logger: InferenceLogger,  # [추가] 데이터 로거
    vocab: Any,                    # [추가] 단어 ID 조회용
    session_id: str = "unknown",
    top_k: int = 3,
    required_frames: int = 128
) -> Optional[Dict[str, Any]]:
    """
    버퍼 데이터를 사용하여 추론을 수행하고, 상세 로그 및 데이터 저장을 수행합니다.
    """
    # HTTP 요청 대응: 버퍼가 부족하면 마지막 프레임을 복제해서라도 채움 (Padding)
    buffer_len = len(frame_buffer)
    if buffer_len == 0:
        return None

    working_buffer = list(frame_buffer)

    # [Code 1의 패딩 로직 유지] HTTP 단발성 요청 처리를 위해 필수
    if buffer_len < required_frames:
        # logger.debug(f"[{session_id}] 버퍼 부족({buffer_len}/{required_frames}). 패딩 수행.")
        while len(working_buffer) < required_frames:
            working_buffer.append(working_buffer[-1])

    try:
        start_time = time.perf_counter()
        # required_frames 개수만큼만 잘라서 사용
        input_tensor = np.stack(working_buffer[:required_frames], axis=0)

        # 1. 데이터 유효성 검증
        keypoints_for_val = input_tensor.reshape(required_frames, 137, 2)
        val_res = validator.validate_sequence(keypoints_for_val, skip_head_occlusion=True)

        # 품질 이슈가 있어도 일단 추론은 진행하되, 로그에 남김
        if not val_res['is_valid']:
            pass # 필요 시 debug 로그 추가 가능

        # 2. 모델 추론
        result = service.predict(input_tensor, return_probabilities=True, top_k=top_k)
        elapsed = (time.perf_counter() - start_time) * 1000

        prediction = result['top_prediction']
        confidence = float(result['top_confidence'])

        # 3. [상세 로깅] Code 2 스타일 적용
        status_tag = "✅ Accepted" if confidence > 60.0 else "⚠️ Low Conf"

        # HTTP 요청인 경우와 WS인 경우 구분을 위해 세션 ID 활용
        req_type = "HTTP" if session_id == "HTTP_REQ" else "WS"

        log_msg = (f"[{session_id}] {status_tag} | "
                   f"예측: '{prediction}' ({confidence:.1f}%) | "
                   f"시간: {elapsed:.1f}ms | 품질: {val_res['quality_score']:.2f}")
        logger.info(log_msg)

        # 4. [데이터 저장] InferenceLogger 사용
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
logger.info(f"⚙️ 설정 완료: Window Size={MAX_BUFFER_FRAMES}, Stride={INFERENCE_STRIDE}")

# --- [추가] 데이터 로거 설정 ---
data_config = config.get_data_config()
DATA_LOGGER = InferenceLogger(
    win=MAX_BUFFER_FRAMES,
    save_dir=data_config.get('save_dir', "data"),   # data 폴더에 저장
    prefix="server_inference",                      # 파일명 접두사
    save_csv_summary=True,                          # CSV 요약본 저장
    save_windows_csv=False                          # 전체 텐서 저장은 끔 (용량 절약)
)
# 서버 종료 시(Ctrl+C) 자동으로 save() 호출
atexit.register(DATA_LOGGER.save)
logger.info("💾 데이터 로거 활성화됨 (종료 시 'data/' 저장)")
# ----------------------------------------------

validator_config = realtime_config.get('validator', {})
GLOBAL_VALIDATOR = AdvancedHandValidator(
    head_occlusion_threshold=validator_config.get('head_occlusion_threshold', 0.8),
    min_hand_movement=validator_config.get('min_hand_movement', 0.01),
    max_frame_gap=validator_config.get('max_frame_gap', 10),
    min_valid_frames_ratio=validator_config.get('min_valid_frames_ratio', 0.3)
)

# =============================================================================
# [ROUTE] HTTP POST (자바 백엔드 연동용)
# =============================================================================
@app.route('/predict_keypoints', methods=['POST'])
def http_predict_keypoints():
    """
    자바 백엔드에서 오는 데이터를 구조에 맞게 변환하여 추론합니다.
    """
    try:
        data = request.get_json()
        session_id = "HTTP_REQ"

        keypoint_input = data.get('keypointData')

        if not keypoint_input:
            return jsonify({"error": "No keypoint data provided"}), 400

        final_keypoints = []

        # 자바 구조 처리: { "keypoints": [...] } 또는 { "body": ..., "face": ... }
        if isinstance(keypoint_input, dict):
            if 'keypoints' in keypoint_input:
                final_keypoints = keypoint_input['keypoints']
                # logger.info(f"단일 리스트 데이터 수신: {len(final_keypoints)}개")
            else:
                body = keypoint_input.get('body') or []
                face = keypoint_input.get('face') or []
                left_hand = keypoint_input.get('leftHand') or []
                right_hand = keypoint_input.get('rightHand') or []
                final_keypoints = body + face + left_hand + right_hand
                # logger.info(f"분할 데이터 수신 및 합체 완료")

        elif isinstance(keypoint_input, list):
            final_keypoints = keypoint_input
        else:
            return jsonify({"error": "Unknown data format"}), 400

        if len(final_keypoints) == 0:
            logger.error("추출된 키포인트가 0개입니다. (데이터 매핑 실패)")
            return jsonify({"error": "Extracted keypoints are empty"}), 400

        # 전처리
        feature_vector = preprocess_frame(final_keypoints)

        if feature_vector is None:
            return jsonify({"error": "Preprocessing failed"}), 400

        # 임시 버퍼 및 추론
        # HTTP 요청은 보통 단발성이므로, 이 1개의 프레임을 버퍼에 넣고
        # execute_inference 내부에서 패딩(복제)하여 128개로 만듭니다.
        temp_buffer = deque([feature_vector])

        result = execute_inference(
            frame_buffer=temp_buffer,
            service=SERVICE,
            validator=GLOBAL_VALIDATOR,
            data_logger=DATA_LOGGER,  # 로거 전달
            vocab=VOCAB,              # 단어장 전달
            session_id=session_id,
            required_frames=MAX_BUFFER_FRAMES
        )

        if result and "type" not in result:
            return jsonify(result)
        else:
            # 실패해도 200 OK로 빈 값 반환 (자바 에러 방지)
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
                # 클라이언트 재시작 감지 (프레임 인덱스가 뒤로 갔을 때)
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

                    if len(frame_buffer) == MAX_BUFFER_FRAMES and \
                       frames_since_last_inference >= INFERENCE_STRIDE:

                        result = execute_inference(
                            frame_buffer=frame_buffer,
                            service=SERVICE,
                            validator=GLOBAL_VALIDATOR,
                            data_logger=DATA_LOGGER,  # 로거 전달
                            vocab=VOCAB,              # 단어장 전달
                            session_id=session_id,
                            required_frames=MAX_BUFFER_FRAMES
                        )

                        if result:
                            if "type" in result and result["type"] == "ERROR":
                                logger.error(f"[{session_id}] 추론 에러: {result['message']}")
                            else:
                                ws.send(json.dumps(result))

                        frames_since_last_inference = 0

        except Exception as e:
            logger.error(f"WS Error: {e}")
            break

    logger.info(f"👋 연결 완전 종료: {session_id}")

if __name__ == '__main__':
    logger.info("🚀 Flask 앱 실행 중 (Port: 5001)...")
    app.run(host='0.0.0.0', port=5001, debug=False)