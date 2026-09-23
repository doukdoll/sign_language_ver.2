from threading import Lock
from typing import Optional, List

import numpy as np
from flask_sock import Sock
from simple_websocket.errors import ConnectionClosed
from realtime.http_api import create_app
from realtime.sessions import SessionManager, serve_connection

# --- 사용자 정의 모듈 임포트 ---
from realtime.inference_utils import (
    load_model_and_vocab,
    normalize_keypoints_by_bodypart
)
from utils.logger import get_logger
from utils.config import load_config, get_default_config_path

# =============================================================================
# [SETUP] 로거 및 설정 초기화
# =============================================================================
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


# =============================================================================
# [SERVER INIT] Flask 및 모델 로드
# =============================================================================
MODEL_PATH = "deployment/20251109-1439_Attention/20251109-1439.onnx"
VOCAB_PATH = "deployment/20251109-1439_Attention/vocabulary.txt"
MODEL_TYPE = "onnx"

logger.info("🚀 서버 시작: 모델 및 리소스 로딩 중...")
realtime_config = config.get_realtime_config()
inference_lock = Lock()

try:
    SERVICE, VOCAB, DEVICE = load_model_and_vocab(MODEL_PATH, VOCAB_PATH, "auto", MODEL_TYPE)
    logger.info(f"✅ 모델 로드 성공 (Device: {DEVICE}, Type: {MODEL_TYPE})")
except Exception as e:
    logger.critical(f"❌ 치명적 오류: 모델 로드 실패. 서버를 종료해야 합니다. {e}", exc_info=True)
    SERVICE, VOCAB, DEVICE = None, None, None

MAX_BUFFER_FRAMES = realtime_config.get('window_size', 200) if MODEL_TYPE == "pytorch" else 128
logger.info(f"⚙️ 설정 완료: Window Size={MAX_BUFFER_FRAMES}, Stride={INFERENCE_STRIDE}")


def predict_window(frames):
    """Serialize HTTP and WebSocket access to the shared model, not their buffers."""
    with inference_lock:
        result = SERVICE.predict(np.stack(frames), return_probabilities=True, top_k=3)
    return result['top_prediction'], float(result['top_confidence'])


def predict_http_frame(feature):
    # Preserve the legacy single-frame repetition and model-side zero padding.
    return predict_window([feature] * MAX_BUFFER_FRAMES)


app = create_app(preprocess_frame, predict_http_frame, ready=lambda: SERVICE is not None)
sock = Sock(app)

# =============================================================================
# [ROUTE] WebSocket protocol v1
# =============================================================================
@sock.route('/ws/predict')
def websocket_predict(ws):
    logger.info("🔗 WebSocket 클라이언트 연결됨")

    manager = SessionManager(
        preprocess_frame, predict_window,
        window_size=MAX_BUFFER_FRAMES, stride=INFERENCE_STRIDE,
        idle_timeout=realtime_config.get('session_idle_timeout', 120.0),
        ready=lambda: SERVICE is not None,
    )
    try:
        serve_connection(ws, manager)
    except ConnectionClosed:
        logger.info("WebSocket closed; connection-owned sessions released")
    except Exception:
        logger.exception("WebSocket transport failed; sessions released")

if __name__ == '__main__':
    logger.info("🚀 Flask 앱 실행 중 (Port: 5001)...")
    # 포트 5001 유지 (자바와 동일하게)
    app.run(host='0.0.0.0', port=5001, debug=False)
