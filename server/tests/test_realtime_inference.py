"""
추론 모델만으로 실시간 수어 인식 테스트
카메라 입력 → 키포인트 추출 → 모델 추론 → 결과 출력
"""

import cv2
import mediapipe as mp
import numpy as np
from collections import deque
import time
from typing import Optional
import os
import sys

# 프로젝트 루트 경로를 sys.path에 추가 (tests/ 폴더에서 실행 시 필요)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from input_keypoint.mediapipe_to_openpose import (
    mediapipe_to_openpose_body25,
    mediapipe_to_openpose_face,
    mediapipe_to_openpose_hand,
)
from input_keypoint.bodypart_normalization_processor import BodyPartNormalizationProcessor
from deployment.inference_service import SignLanguageInferenceService
from utils.logger import get_logger
from utils.config import load_config

logger = get_logger("kslt.test_realtime")


class RealtimeInferenceTest:
    """추론 모델만으로 실시간 수어 인식 테스트"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        테스트 초기화
        
        Args:
            config_path: 설정 파일 경로 (None이면 기본 설정 사용)
        """
        # 프로젝트 루트 경로 설정
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 설정 로딩 (프로젝트 루트 기준 절대 경로)
        if config_path is None:
            config_path = os.path.join(self.project_root, "config", "test_config.yaml")
        elif not os.path.isabs(config_path):
            # 상대 경로인 경우 프로젝트 루트 기준으로 변환
            config_path = os.path.join(self.project_root, config_path)
        
        self.config = load_config(config_path)
        
        # 모델 설정 추출
        model_config = self.config.get_model_config()
        
        # 모델 경로를 절대 경로로 변환
        model_path = model_config.get('path', "deployment/multi_class_auto/multi_class_auto_model.pt")
        if not os.path.isabs(model_path):
            self.model_path = os.path.join(self.project_root, model_path)
        else:
            self.model_path = model_path
        
        # vocab 경로를 절대 경로로 변환
        vocab_path = model_config.get('vocab_path', "deployment/multi_class_auto/vocabulary.txt")
        if not os.path.isabs(vocab_path):
            self.vocab_path = os.path.join(self.project_root, vocab_path)
        else:
            self.vocab_path = vocab_path
        
        self.device = model_config.get('device', "auto")
        self.model_type = model_config.get('type', "pytorch")
        
        # 실시간 설정 추출
        realtime_config = self.config.get_realtime_config()
        self.WIN_SIZE = realtime_config.get('window_size', 200)
        self.fps_target = realtime_config.get('fps_target', 30.0)
        
        # 테스트 설정 추출
        test_config = self.config.get('test', {})
        self.test_config = test_config
        
        # 추론 서비스 초기화
        self.service = SignLanguageInferenceService(
            model_path=self.model_path,
            vocab_path=self.vocab_path,
            device=self.device,
            model_type=self.model_type
        )
        
        # MediaPipe 초기화
        self.mp_holistic = mp.solutions.holistic
        self.mp_drawing = mp.solutions.drawing_utils
        
        # 정규화 설정 로딩
        normalization_config = realtime_config.get('normalization', {})
        
        # 신체 부위별 정규화 프로세서 초기화 (항상 사용)
        self.normalization_processor = BodyPartNormalizationProcessor(
            image_width=normalization_config.get('image_width', 640),
            image_height=normalization_config.get('image_height', 480),
            confidence_threshold=normalization_config.get('confidence_threshold', 0.3),
            bbox_padding=normalization_config.get('bbox_padding', 0.1)
        )
        
        # 실시간 추론 설정
        self.feat_buffer = deque(maxlen=self.WIN_SIZE)
        
        # 성능 측정
        self.frame_count = 0
        self.start_time = time.time()
        
        logger.info("실시간 추론 테스트 초기화 완료")
        logger.info(f"설정 파일: {config_path}")
        logger.info(f"모델: {self.model_path}")
        logger.info(f"어휘: {self.vocab_path}")
        logger.info(f"디바이스: {self.service.device}")
        logger.info(f"클래스 수: {len(self.service.vocab)}")
        logger.info(f"윈도우 크기: {self.WIN_SIZE}")
        logger.info("신체 부위별 정규화 프로세서 활성화")
    
    def setup_camera(self, camera_index: int = 0) -> cv2.VideoCapture:
        """카메라 설정"""
        # 카메라 설정 로딩
        realtime_config = self.config.get_realtime_config()
        camera_config = realtime_config.get('camera', {})
        
        # 다양한 카메라 인덱스 시도
        cap = None
        camera_indices = camera_config.get('indices', [0, 1, 2])
        
        for idx in camera_indices:
            logger.info(f"카메라 인덱스 {idx}를 시도합니다...")
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                ret, test_frame = cap.read()
                if ret:
                    logger.info(f"카메라 인덱스 {idx}에서 성공적으로 연결되었습니다.")
                    break
                else:
                    cap.release()
                    cap = None
            else:
                if cap:
                    cap.release()
                cap = None
        
        if cap is None:
            raise RuntimeError("사용 가능한 카메라를 찾을 수 없습니다")
        
        # 카메라 설정 최적화
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, camera_config.get('width', 640))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_config.get('height', 480))
        cap.set(cv2.CAP_PROP_FPS, camera_config.get('fps', 30))
        
        logger.info(f"카메라 설정 완료: {camera_config.get('width', 640)}x{camera_config.get('height', 480)}")
        return cap
    
    def extract_keypoints(self, results, frame_width: int = 640, frame_height: int = 480) -> np.ndarray:
        """
        MediaPipe 결과에서 키포인트 추출 및 신체 부위별 정규화 적용
        
        bodypart_normalization_processor.py와 동일한 방식으로 처리:
        1. MediaPipe → OpenPose 형식 변환
        2. 신체 부위별 정규화 (Pose: 화면 기준, Face/Hands: bbox 기준)
        3. Pose만 코 기준 상대 좌표 변환
        4. x, y 좌표만 추출하여 274차원 벡터로 변환
        """
        # 키포인트 추출
        body_keypoints = mediapipe_to_openpose_body25(results, 1, 1) if results.pose_landmarks else np.zeros((25, 3))
        face_keypoints = mediapipe_to_openpose_face(results, 1, 1) if results.face_landmarks else np.zeros((70, 3))
        all_hand_keypoints = mediapipe_to_openpose_hand(results, 1, 1)
        lh_keypoints = all_hand_keypoints[:21]
        rh_keypoints = all_hand_keypoints[21:]
        
        # 전체 키포인트 배열 구성 (137, 3) - x, y, confidence
        all_keypoints = np.vstack([
            body_keypoints,    # 25개 포즈 키포인트
            face_keypoints,    # 70개 얼굴 키포인트
            lh_keypoints,      # 21개 왼손 키포인트
            rh_keypoints       # 21개 오른손 키포인트
        ]).astype(np.float32)
        
        # NaN 처리
        all_keypoints = np.nan_to_num(all_keypoints, nan=0.0, posinf=0.0, neginf=0.0)
        
        # ★★★ 신체 부위별 정규화 적용 ★★★
        normalized_keypoints = self.normalization_processor.normalize_keypoints_by_bodypart(
            all_keypoints, 
            width=frame_width, 
            height=frame_height
        )
        
        # 상대 위치 변환 (Pose만 코 기준)
        relative_keypoints = self.normalization_processor.convert_to_relative_vectorized(normalized_keypoints)
        
        # x, y 좌표만 추출하여 274차원 벡터로 변환
        xy = relative_keypoints[:, :2].reshape(-1).astype(np.float32)
        
        return xy  # 274차원 1D 벡터
    
    def run_inference_test(self, camera_index: int = 0):
        """실시간 추론 테스트 실행"""
        cap = self.setup_camera(camera_index)
        
        # 성능 측정 변수
        fps_counter = 0
        fps_start_time = time.time()
        current_fps = 0
        
        # 최근 예측 결과 저장
        recent_predictions = deque(maxlen=10)
        
        # MediaPipe 설정 로딩
        realtime_config = self.config.get_realtime_config()
        mediapipe_config = realtime_config.get('mediapipe', {})
        
        # 테스트 설정 로딩
        realtime_test_config = self.test_config.get('realtime_test', {})
        log_interval = realtime_test_config.get('log_interval', 30)
        top_k_predictions = realtime_test_config.get('top_k_predictions', 3)
        
        try:
            with self.mp_holistic.Holistic(
                min_detection_confidence=mediapipe_config.get('min_detection_confidence', 0.5),
                min_tracking_confidence=mediapipe_config.get('min_tracking_confidence', 0.5)
            ) as holistic:
                
                logger.info("실시간 추론 테스트 시작 (종료: 'q' 키)")
                
                while cap.isOpened():
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("프레임 읽기 실패")
                        continue
                    
                    # MediaPipe 처리
                    image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = holistic.process(image)
                    
                    # 키포인트 추출 (프레임 해상도 정보 포함)
                    frame_height, frame_width = frame.shape[:2]
                    keypoints = self.extract_keypoints(results, frame_width, frame_height)
                    self.feat_buffer.append(keypoints)
                    
                    # 충분한 프레임이 쌓이면 추론 수행
                    if len(self.feat_buffer) >= self.WIN_SIZE:
                        # 최근 프레임들을 스택으로 변환
                        input_data = np.stack(list(self.feat_buffer), axis=0)
                        
                        # 모델 추론
                        start_inference = time.time()
                        result = self.service.predict(
                            input_data, 
                            return_probabilities=True, 
                            top_k=top_k_predictions
                        )
                        inference_time = time.time() - start_inference
                        
                        # 결과 처리
                        top_prediction = result['top_prediction']
                        confidence = result['top_confidence']
                        
                        # 최근 예측에 추가
                        recent_predictions.append({
                            'word': top_prediction,
                            'confidence': confidence,
                            'timestamp': time.time()
                        })
                        
                        # 디버깅 출력 (설정된 간격마다)
                        if self.frame_count % log_interval == 0:
                            logger.info(f"예측: {top_prediction} ({confidence:.1f}%) - 추론시간: {inference_time*1000:.1f}ms")
                        
                        # 상위 k개 예측 출력 (매 2*log_interval 프레임마다)
                        if self.frame_count % (2 * log_interval) == 0:
                            logger.info(f"상위 {top_k_predictions}개 예측:")
                            for i, pred in enumerate(result['top_k_predictions']):
                                logger.info(f"  {i+1}. {pred['word']}: {pred['confidence']:.1f}%")
                    
                    # FPS 계산
                    fps_counter += 1
                    if fps_counter >= 30:
                        current_fps = fps_counter / (time.time() - fps_start_time)
                        fps_counter = 0
                        fps_start_time = time.time()
                    
                    # 시각화
                    image.flags.writeable = True
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    
                    # 시각화 설정 로딩
                    show_confidence = realtime_test_config.get('show_confidence', True)
                    show_fps = realtime_test_config.get('show_fps', True)
                    show_frame_count = realtime_test_config.get('show_frame_count', True)
                    show_landmarks = realtime_test_config.get('show_landmarks', True)
                    
                    # 최근 예측 결과 표시
                    if recent_predictions and show_confidence:
                        latest = recent_predictions[-1]
                        text = f"{latest['word']} ({latest['confidence']:.1f}%)"
                        
                        # 배경 사각형
                        cv2.rectangle(image, (10, 10), (600, 50), (0, 0, 0), -1)
                        cv2.putText(image, text, (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    
                    # FPS 표시
                    if show_fps:
                        cv2.putText(image, f"FPS: {current_fps:.1f}", (10, 70), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # 프레임 수 표시
                    if show_frame_count:
                        cv2.putText(image, f"Frame: {self.frame_count}", (10, 90), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
                    
                    # 랜드마크 표시
                    if show_landmarks:
                        self.mp_drawing.draw_landmarks(image, results.right_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS)
                        self.mp_drawing.draw_landmarks(image, results.left_hand_landmarks, self.mp_holistic.HAND_CONNECTIONS)
                        self.mp_drawing.draw_landmarks(image, results.pose_landmarks, self.mp_holistic.POSE_CONNECTIONS)
                    
                    # 화면 출력
                    cv2.imshow('Real-time Inference Test', image)
                    
                    # 종료 조건
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                    
                    self.frame_count += 1
                    
        except KeyboardInterrupt:
            logger.info("사용자에 의해 중단됨")
        except Exception as e:
            logger.error(f"실시간 추론 중 오류: {e}")
        finally:
            cap.release()
            cv2.destroyAllWindows()
            
            # 최종 통계
            total_time = time.time() - self.start_time
            avg_fps = self.frame_count / total_time if total_time > 0 else 0
            
            logger.info("=" * 50)
            logger.info("실시간 추론 테스트 완료")
            logger.info(f"총 프레임: {self.frame_count}")
            logger.info(f"총 시간: {total_time:.1f}초")
            logger.info(f"평균 FPS: {avg_fps:.1f}")
            logger.info("=" * 50)
    
    def test_with_sample_data(self):
        """샘플 데이터로 모델 테스트"""
        logger.info("샘플 데이터로 모델 테스트 시작")
        
        # 설정에서 테스트 케이스 로딩
        sample_data_tests = self.test_config.get('sample_data_tests', [])
        
        # 기본 테스트 케이스가 없으면 기본값 사용
        if not sample_data_tests:
            sample_data_tests = [
                {"name": "랜덤 데이터", "type": "random", "params": {"mean": 0.0, "std": 1.0}},
                {"name": "영점 데이터", "type": "zeros"},
                {"name": "일정한 값", "type": "constant", "params": {"value": 0.5}},
                {"name": "정규분포", "type": "normal", "params": {"mean": 0.0, "std": 1.0}},
            ]
        
        for test_case in sample_data_tests:
            name = test_case['name']
            test_type = test_case['type']
            params = test_case.get('params', {})
            
            logger.info(f"\n--- {name} 테스트 ---")
            
            try:
                # 테스트 데이터 생성
                if test_type == "random":
                    data = np.random.randn(self.WIN_SIZE, 274).astype(np.float32)
                elif test_type == "zeros":
                    data = np.zeros((self.WIN_SIZE, 274), dtype=np.float32)
                elif test_type == "constant":
                    value = params.get('value', 0.5)
                    data = np.full((self.WIN_SIZE, 274), value, dtype=np.float32)
                elif test_type == "normal":
                    mean = params.get('mean', 0.0)
                    std = params.get('std', 1.0)
                    data = np.random.normal(mean, std, (self.WIN_SIZE, 274)).astype(np.float32)
                else:
                    logger.warning(f"알 수 없는 테스트 타입: {test_type}")
                    continue
                
                result = self.service.predict(
                    data, 
                    return_probabilities=True, 
                    top_k=5
                )
                
                logger.info(f"예측 결과: {result['top_prediction']}")
                logger.info(f"신뢰도: {result['top_confidence']:.2f}%")
                
                logger.info("상위 5개 예측:")
                for i, pred in enumerate(result['top_k_predictions']):
                    logger.info(f"  {i+1}. {pred['word']}: {pred['confidence']:.2f}%")
                    
            except Exception as e:
                logger.error(f"{name} 테스트 실패: {e}")
        
        logger.info("샘플 데이터 테스트 완료")


def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="추론 모델만으로 실시간 수어 인식 테스트")
    parser.add_argument("--config", type=str, default=None, 
                       help="설정 파일 경로 (기본값: config/test_config.yaml)")
    parser.add_argument("--sample-only", action="store_true", 
                       help="샘플 데이터 테스트만 실행")
    parser.add_argument("--realtime-only", action="store_true", 
                       help="실시간 테스트만 실행")
    
    args = parser.parse_args()
    
    try:
        # 테스트 인스턴스 생성
        test = RealtimeInferenceTest(config_path=args.config)
        
        if args.sample_only:
            # 샘플 데이터 테스트만
            test.test_with_sample_data()
        elif args.realtime_only:
            # 실시간 카메라 테스트만
            print("\n실시간 카메라 테스트를 시작합니다...")
            print("종료하려면 'q' 키를 누르세요.")
            test.run_inference_test(camera_index=0)
        else:
            # 전체 테스트
            # 샘플 데이터 테스트
            test.test_with_sample_data()
            
            # 실시간 카메라 테스트
            print("\n실시간 카메라 테스트를 시작합니다...")
            print("종료하려면 'q' 키를 누르세요.")
            test.run_inference_test(camera_index=0)
        
    except FileNotFoundError as e:
        logger.error(f"파일을 찾을 수 없습니다: {e}")
        logger.info("모델 파일과 어휘 사전 파일 경로를 확인해주세요.")
    except Exception as e:
        logger.error(f"테스트 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
