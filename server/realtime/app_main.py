import atexit
import time
from collections import deque
from typing import Optional, Dict, Any

import cv2
import mediapipe as mp
import numpy as np
import torch
import torch.nn.functional as F

from input_keypoint.mediapipe_to_openpose import (
    mediapipe_to_openpose_body25,
    mediapipe_to_openpose_face,
    mediapipe_to_openpose_hand,
)
from input_keypoint.advanced_validators import AdvancedHandValidator
from realtime.segmenter import OnlineSegmenter, hand_speed
from realtime.visualization import draw_text_korean
from realtime.inference_logger import InferenceLogger
from realtime.inference_utils import (
    load_model_and_vocab, 
    preprocess_keypoints, 
    predict, 
    normalize_keypoints_by_bodypart
)
from utils.logger import get_logger
from utils.config import load_config, get_default_config_path
from utils.exceptions import ModelLoadingError, CameraError, ConfigurationError
from utils.performance import performance_optimizer, optimize_tensor_operations, profile_function

logger = get_logger("kslt.realtime")


def realtime_translation(config_path: Optional[str] = None) -> None:
    """실시간 수어 번역을 수행합니다."""
    # --- 1. 설정 로딩 ---
    if config_path is None:
        config_path = get_default_config_path()
    
    config = load_config(config_path)
    
    # 설정에서 값 추출
    model_config = config.get_model_config()
    MODEL_PATH = model_config.get('path', "deployment/multi_class_auto/multi_class_auto_model.pt")
    VOCAB_PATH = model_config.get('vocab_path', "deployment/multi_class_auto/vocabulary.txt")
    MODEL_TYPE = model_config.get('type', "pytorch")
    DEVICE = model_config.get('device', "auto")
    
    try:
        service, vocab, device = load_model_and_vocab(MODEL_PATH, VOCAB_PATH, DEVICE, MODEL_TYPE)
    except (FileNotFoundError, ModelLoadingError) as e:
        logger.error(f"배포 모델 또는 어휘 사전 로딩에 실패했습니다: {e}")
        return

    # MediaPipe 초기화
    mp_holistic = mp.solutions.holistic
    mp_drawing = mp.solutions.drawing_utils

    LEFT_EYE_INDICES = [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246]
    RIGHT_EYE_INDICES = [362, 382, 381, 380, 374, 373, 390, 249, 263, 466, 388, 387, 386, 385, 384, 398]
    MOUTH_INDICES = [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78]
    NOSE_INDICES = [1, 2, 98, 327, 168, 197, 5, 195, 4]

    # 카메라 설정 로딩
    realtime_config = config.get_realtime_config()
    camera_config = realtime_config.get('camera', {})
    mediapipe_config = realtime_config.get('mediapipe', {})
    
    # 다양한 카메라 인덱스 시도
    cap = None
    camera_indices = camera_config.get('indices', [0, 1, 2])
    for camera_index in camera_indices:
        logger.info(f"카메라 인덱스 {camera_index}를 시도합니다...")
        cap = cv2.VideoCapture(camera_index)
        if cap.isOpened():
            ret, test_frame = cap.read()
            if ret:
                logger.info(f"카메라 인덱스 {camera_index}에서 성공적으로 연결되었습니다.")
                break
            else:
                cap.release()
                cap = None
        else:
            if cap:
                cap.release()
            cap = None

    if cap is None:
        error_msg = "사용 가능한 카메라를 찾을 수 없습니다."
        logger.error(error_msg)
        logger.info("해결 방법:")
        logger.info("1. 다른 앱(Zoom, Teams 등)에서 카메라를 사용 중인지 확인하세요.")
        logger.info("2. 시스템 설정 > 보안 및 개인 정보 보호 > 카메라에서 Python 권한을 확인하세요.")
        logger.info("3. 카메라가 제대로 연결되었는지 확인하세요.")
        raise CameraError(error_msg, camera_index=None)

    # 카메라 설정 최적화
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config.get('width', 640))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config.get('height', 480))
    cap.set(cv2.CAP_PROP_FPS, camera_config.get('fps', 30))

    # 시퀀스/세그멘테이션 상태
    sentence = []  # 인식된 수어 단어들
    # 배포 모델에 맞게 윈도우 크기 조정 (PyTorch: 200, ONNX: 128)
    WIN = realtime_config.get('window_size', 200) if MODEL_TYPE == "pytorch" else 128
    feat_buf = deque(maxlen=WIN)  # 최근 프레임 키포인트 버퍼 (274차원 벡터들)
    prev_lh = None  # 이전 프레임 왼손 좌표 (속도 계산용)
    prev_rh = None  # 이전 프레임 오른손 좌표 (속도 계산용)
    
    # 화면 표시용 변수
    current_prediction = ""
    current_confidence = 0.0
    current_inference_time = 0.0

    # 데이터 저장 설정 로딩
    data_config = config.get_data_config()
    logger_instance = InferenceLogger(
        win=WIN,
        save_dir=data_config.get('save_dir', "data"),
        prefix=data_config.get('prefix', "inference_keypoints"),
        save_csv_summary=data_config.get('save_csv_summary', True),
        save_windows_csv=data_config.get('save_windows_csv', False),
    )
    atexit.register(logger_instance.save)

    # Blank 라벨 id 추정 (무의미한 동작 필터링용)
    blank_id = None
    if hasattr(vocab, 'stoi'):
        blank_id = vocab.stoi.get('Blank', None) or vocab.stoi.get('<blank>', None)

    # 세그멘테이션 설정 로딩
    segmenter_config = config.get_segmenter_config()
    fps_target = realtime_config.get('fps_target', 30.0)
    segmenter = OnlineSegmenter(
        prob_thr=segmenter_config.get('prob_thr', 0.3),
        fuse_tau=segmenter_config.get('fuse_tau', 0.4),
        min_on=segmenter_config.get('min_on', 3),
        cooldown=segmenter_config.get('cooldown', 14),
        w_motion=segmenter_config.get('w_motion', 0.5),
        w_prob=segmenter_config.get('w_prob', 0.5),
        blank_id=blank_id,
        rearm_tau=segmenter_config.get('rearm_tau', 0.40),
        rearm_off=segmenter_config.get('rearm_off', 10),
    )
    
    # 고급 검증기 초기화 (머리 겹침 체크 제외)
    validator_config = realtime_config.get('validator', {})
    validator = AdvancedHandValidator(
        head_occlusion_threshold=validator_config.get('head_occlusion_threshold', 0.8),
        min_hand_movement=validator_config.get('min_hand_movement', 0.01),  # 실시간용 낮은 임계값
        max_frame_gap=validator_config.get('max_frame_gap', 10),  # 실시간용 더 관대한 gap
        min_valid_frames_ratio=validator_config.get('min_valid_frames_ratio', 0.3)  # 실시간용 낮은 비율
    )

    # FPS 측정 상태
    t_last = time.perf_counter()
    frame_counter = 0
    fps_smoothed = fps_target
    
    # 로깅 설정
    log_interval = realtime_config.get('log_interval', 30)  # 로그 출력 간격 (프레임)
    top_k_log = realtime_config.get('top_k_log', 3)  # 상위 k개 예측 로그
    inference_frame_counter = 0  # 추론 프레임 카운터

    with mp_holistic.Holistic(
        min_detection_confidence=mediapipe_config.get('min_detection_confidence', 0.5),
        min_tracking_confidence=mediapipe_config.get('min_tracking_confidence', 0.5)
    ) as holistic:
        frame_failures = 0
        max_failures = camera_config.get('max_failures', 10)

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                frame_failures += 1
                if frame_failures >= max_failures:
                    logger.error(f"{max_failures}번 연속으로 프레임을 읽을 수 없습니다. 프로그램을 종료합니다.")
                    break
                logger.warning(f"프레임 읽기 실패 ({frame_failures}/{max_failures})")
                continue
            else:
                frame_failures = 0

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = holistic.process(image)

            # --- 키포인트 추출 (MediaPipe → OpenPose 형식) ---
            with performance_optimizer.memory_monitor("keypoint_extraction"):
                body_keypoints = mediapipe_to_openpose_body25(results, 1, 1) if results.pose_landmarks else np.zeros((25, 3))
                face_keypoints = mediapipe_to_openpose_face(results, 1, 1) if results.face_landmarks else np.zeros((70, 3))
                all_hand_keypoints = mediapipe_to_openpose_hand(results, 1, 1)
                lh_keypoints = all_hand_keypoints[:21]
                rh_keypoints = all_hand_keypoints[21:]

                # 모든 키포인트 결합 (137, 3)
                all_keypoints = np.vstack([
                    body_keypoints,   # (25, 3)
                    face_keypoints,   # (70, 3)
                    lh_keypoints,     # (21, 3)
                    rh_keypoints      # (21, 3)
                ])  # (137, 3)

                # === 신체 부위별 정규화 적용 ===
                normalized_keypoints = normalize_keypoints_by_bodypart(
                    all_keypoints,
                    width=1.0,  # MediaPipe는 이미 0-1 범위로 정규화됨
                    height=1.0
                )

                # 다시 신체 부위별로 분리
                body_keypoints = normalized_keypoints[0:25]
                face_keypoints = normalized_keypoints[25:95]
                lh_keypoints = normalized_keypoints[95:116]
                rh_keypoints = normalized_keypoints[116:137]

                # 코 기준 상대 좌표화 (Pose만 적용)
                nose_keypoint = body_keypoints[0]
                if nose_keypoint[2] > 0.1:
                    body_keypoints[:, :2] -= nose_keypoint[:2]
                    # Face와 Hands는 이미 바운딩 박스 기준으로 정규화되었으므로 그대로 유지

                # 137개 키포인트의 xy 좌표만 추출 → 274차원 벡터
                xy = np.concatenate([
                    body_keypoints[:, :2],   # 25*2 = 50차원
                    face_keypoints[:, :2],   # 70*2 = 140차원
                    lh_keypoints[:, :2],     # 21*2 = 42차원
                    rh_keypoints[:, :2]      # 21*2 = 42차원
                ], axis=0).astype(np.float32)  # 총 274차원

            # 키포인트 유효성 마스크 생성
            presence_mask = np.vstack([
                np.full((25, 1), 1.0 if results.pose_landmarks is not None else 0.0, dtype=np.float32),
                np.full((70, 1), 1.0 if results.face_landmarks is not None else 0.0, dtype=np.float32),
                np.full((21, 1), 1.0 if results.left_hand_landmarks is not None else 0.0, dtype=np.float32),
                np.full((21, 1), 1.0 if results.right_hand_landmarks is not None else 0.0, dtype=np.float32)
            ])
            coord_mask = (~np.isnan(xy).any(axis=1)).astype(np.float32).reshape(-1, 1)
            mask = presence_mask * coord_mask
            xy = np.nan_to_num(xy, nan=0.0, posinf=0.0, neginf=0.0)
            xy *= mask

            feat = xy.reshape(-1)  # 274차원 1D 벡터로 변환
            feat_buf.append(feat)

            # 손 이동 거리 계산 (스칼라 속도값)
            spd = hand_speed(prev_lh, prev_rh, lh_keypoints, rh_keypoints)
            prev_lh = lh_keypoints.copy()
            prev_rh = rh_keypoints.copy()

            # --- 슬라이딩 윈도우 추론 + 세그멘테이션 ---
            if len(feat_buf) >= WIN:
                inference_frame_counter += 1
                
                with performance_optimizer.memory_monitor("inference"):
                    arr = np.stack(list(feat_buf)[-WIN:], axis=0)  # 최근 프레임 추출 → (WIN, 274)
                    
                    # === 고급 검증 수행 (머리 겹침 체크 제외) ===
                    # 274차원 벡터를 137개 키포인트 (x,y) 형태로 변환
                    keypoints_for_validation = arr.reshape(WIN, 137, 2)
                    validation_result = validator.validate_sequence(keypoints_for_validation, skip_head_occlusion=True)
                    
                    # 검증 실패 시 로그 출력 및 품질 점수 반영
                    if not validation_result['is_valid']:
                        logger.debug(f"윈도우 검증 실패: {validation_result['issues']}, "
                                   f"품질 점수: {validation_result['quality_score']:.2f}")
                    
                    # 추론 시간 측정 시작
                    start_inference = time.perf_counter()
                    
                    # 배포 모델로 추론 (상위 k개 예측 포함)
                    result = service.predict(arr, return_probabilities=True, top_k=top_k_log)
                    
                    # 추론 시간 측정 종료
                    inference_time = time.perf_counter() - start_inference
                
                # 확률 분포 추출
                probs = np.array(result['probabilities'])
                label_id = np.argmax(probs)
                max_prob = probs.max()
                
                # 결과 정보 추출
                top_prediction = result['top_prediction']
                confidence = result['top_confidence']
                
                # === 검증 결과를 신뢰도에 반영 ===
                # 품질 점수가 낮으면 신뢰도를 조정
                adjusted_confidence = confidence * validation_result['quality_score']
                
                # 화면 표시용 변수 업데이트
                current_prediction = top_prediction
                current_confidence = adjusted_confidence
                current_inference_time = inference_time
                
                # === 주기적 로그 출력 ===
                # 기본 예측 결과 로그 (log_interval 프레임마다)
                if inference_frame_counter % log_interval == 0:
                    logger.info(f"예측: {top_prediction} (원본: {confidence:.1f}%, 조정: {adjusted_confidence:.1f}%) "
                               f"- 품질: {validation_result['quality_score']:.2f} - 추론시간: {inference_time*1000:.1f}ms")
                
                # 상위 k개 예측 로그 (2*log_interval 프레임마다)
                if inference_frame_counter % (2 * log_interval) == 0:
                    logger.info(f"상위 {top_k_log}개 예측:")
                    for i, pred in enumerate(result['top_k_predictions']):
                        logger.info(f"  {i+1}. {pred['word']}: {pred['confidence']:.1f}%")
                
                # 디버깅 출력: 모델 예측 결과
                logger.debug(f"최고 확률: {max_prob:.3f}, 예측 라벨: {label_id}, 단어: {vocab.token_from_index_if_valid(label_id)}")
                
                # 세그멘테이션 처리
                segmenter_result = segmenter.update(probs, spd)  # 속도+확률 기반 방출 결정
                
                # 디버깅 출력: 세그멘터 상태
                if hasattr(segmenter, '_on_count'):
                    logger.debug(f"ON 카운트: {segmenter._on_count}/{segmenter_config.get('min_on', 3)}, 속도: {spd:.3f}, 방출: {segmenter_result}")
                
                label_id = segmenter_result
                if label_id is not None:  # 세그멘터가 방출 결정했으면
                    word = vocab.token_from_index_if_valid(label_id)  # 라벨 → 한글 단어
                    if word is not None:
                        # 검증 통과한 경우에만 방출 또는 낮은 품질 경고
                        if validation_result['is_valid']:
                            if len(sentence) == 0 or sentence[-1] != word:
                                sentence.append(word)
                                # 최종 방출된 단어는 항상 로그 출력
                                logger.info(f"✓ 단어 방출: {word} (신뢰도: {adjusted_confidence:.1f}%, "
                                           f"품질: {validation_result['quality_score']:.2f})")
                            logger_instance.add(label_id=label_id, word=word, feat_window=arr)
                        else:
                            # 검증 실패 시 경고와 함께 방출 (사용자가 판단할 수 있도록)
                            if len(sentence) == 0 or sentence[-1] != word:
                                sentence.append(word)
                                logger.warning(f"⚠ 낮은 품질 단어 방출: {word} (신뢰도: {adjusted_confidence:.1f}%, "
                                             f"품질: {validation_result['quality_score']:.2f}) - 이슈: {validation_result['issues']}")
                            logger_instance.add(label_id=label_id, word=word, feat_window=arr)

            # --- FPS 기반 동적 임계값 튜닝 (성능 저하 시 임계값 완화) ---
            frame_counter += 1
            if frame_counter >= 15:  # 15프레임마다 FPS 측정 및 조정
                t_now = time.perf_counter()
                elapsed = t_now - t_last
                if elapsed > 0:
                    fps_curr = frame_counter / elapsed
                    fps_smoothed = 0.7 * fps_smoothed + 0.3 * fps_curr  # 지수 이동 평균
                    ratio = max(0.5, min(1.0, fps_smoothed / fps_target))  # FPS 비율 (50%~100%)
                    segmenter.prob_thr = max(0.4, segmenter_config.get('prob_thr', 0.3) * ratio)
                    segmenter.fuse_tau = max(0.5, segmenter_config.get('fuse_tau', 0.4) * ratio)
                    segmenter.min_on = max(5, int(round(segmenter_config.get('min_on', 3) * ratio)))
                t_last = t_now
                frame_counter = 0

            # --- 시각화 (인식된 단어 화면 표시) ---
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            
            # 시각화 설정 로딩
            viz_config = config.get_visualization_config()
            bg_color = viz_config.get('background_color', [16, 117, 245])
            font_color = viz_config.get('font_color', [255, 255, 255])
            font_size = viz_config.get('font_size', 28)
            show_confidence = viz_config.get('show_confidence', True)
            show_inference_time = viz_config.get('show_inference_time', True)
            
            # 상단 배경 (높이 증가)
            header_height = 80 if (show_confidence or show_inference_time) else 40
            cv2.rectangle(image, (0, 0), (640, header_height), bg_color, -1)
            
            # 메인 텍스트 (최종 방출된 단어)
            text_to_draw = (sentence[-1] if len(sentence) > 0 else "")
            image = draw_text_korean(image, text_to_draw, position=(6, 8), font_size=font_size, font_color=font_color)
            
            # 추가 정보 표시
            if current_prediction and (show_confidence or show_inference_time):
                info_text = f"현재: {current_prediction}"
                if show_confidence:
                    info_text += f" ({current_confidence:.1f}%)"
                if show_inference_time:
                    info_text += f" | {current_inference_time*1000:.1f}ms"
                image = draw_text_korean(image, info_text, position=(6, 42), font_size=18, font_color=font_color)

            # 랜드마크 표시 (설정에 따라)
            if viz_config.get('show_landmarks', True):
                mp_drawing.draw_landmarks(image, results.right_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                mp_drawing.draw_landmarks(image, results.left_hand_landmarks, mp_holistic.HAND_CONNECTIONS)
                mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_holistic.POSE_CONNECTIONS)

            # 화면 출력
            cv2.imshow('Real-time Sign Language Translation', image)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    try:
        logger_instance.save()
        logger.info("추론 로그 저장이 완료되었습니다.")
    except Exception as e:
        logger.error(f"추론 로그 저장 중 오류 발생: {e}")
        logger.warning("추론 로그가 저장되지 않았습니다. 수동으로 확인해주세요.")
    cap.release()
    cv2.destroyAllWindows()


def inference_from_file() -> None:
    """파일로부터 추론을 수행합니다."""
    MODEL_PATH = "deployment/multi_class_auto/multi_class_auto_model.pt"
    VOCAB_PATH = "deployment/multi_class_auto/vocabulary.txt"
    MODEL_TYPE = "pytorch"
    SAMPLE_CSV_PATH = "NIA_SL_WORD0009_REAL01_F_keypoints.csv"

    logger.info("=" * 30)
    logger.info("      배포 모델 추론 시작")
    logger.info("=" * 30)

    try:
        service, vocab, device = load_model_and_vocab(MODEL_PATH, VOCAB_PATH, "auto", MODEL_TYPE)
        input_tensor = preprocess_keypoints(SAMPLE_CSV_PATH)
        prediction = predict(service, input_tensor, vocab, device)
        logger.info("\n" + "=" * 30)
        logger.info(f" 최종 예측 결과: {prediction}")
        logger.info("=" * 30)
    except FileNotFoundError as e:
        logger.error(f"파일 경로를 확인해주세요: {e}")
    except Exception as e:
        logger.error(f"예상치 못한 오류가 발생했습니다: {e}")
