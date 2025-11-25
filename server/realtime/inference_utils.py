import os
import torch
import yaml
import pandas as pd
import numpy as np
import sys
from typing import Tuple, Any, Optional

# 배포 모델 추론 서비스 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'deployment'))
from deployment.inference_service import SignLanguageInferenceService
from utils.logger import get_logger
from utils.exceptions import ModelLoadingError, VocabularyError, DataProcessingError
from utils.performance import optimize_data_loading, profile_function

logger = get_logger("kslt.inference")

# 정규화 상수
CONFIDENCE_THRESHOLD = 0.3
BBOX_PADDING = 0.1


def load_model_and_vocab(
    model_path: str, 
    vocab_path: str, 
    device: str = "auto", 
    model_type: str = "pytorch"
) -> Tuple[SignLanguageInferenceService, Any, torch.device]:
    """
    배포된 모델과 어휘 사전을 로드하여 추론 준비가 된 서비스를 반환합니다.

    Parameters:
        model_path: 배포된 모델 파일 경로 (.pt 또는 .onnx)
        vocab_path: 어휘 사전 텍스트 파일 경로
        device: 실행 디바이스 ("cuda", "cpu", "auto")
        model_type: 모델 타입 ("pytorch" 또는 "onnx")

    Returns:
        (service, vocab_wrapper, device)
    """
    logger.info("배포 모델 로딩 중...")
    
    # 추론 서비스 초기화
    service = SignLanguageInferenceService(
        model_path=model_path,
        vocab_path=vocab_path,
        device=device,
        model_type=model_type
    )
    
    # 어휘 사전 래퍼 클래스 (기존 코드와 호환성 유지)
    class VocabWrapper:
        def __init__(self, vocab_list):
            self.vocab = vocab_list
            self.stoi = {token: i for i, token in enumerate(vocab_list)}
        
        def token_from_index_if_valid(self, index):
            return service.token_from_index_if_valid(index)
    
    vocab_wrapper = VocabWrapper(service.vocab)
    
    logger.info("모델 로딩 완료!")
    return service, vocab_wrapper, service.device


def preprocess_keypoints(csv_path: str) -> torch.Tensor:
    """
    Keypoint가 저장된 CSV 파일을 모델 입력에 맞게 전처리합니다.

    Parameters:
        csv_path: 키포인트 CSV 경로

    Returns:
        전처리된 텐서 (1, seq_len, feat_dim)
    """
    if not os.path.exists(csv_path):
        raise DataProcessingError(
            f"CSV 파일을 찾을 수 없습니다: {csv_path}",
            data_path=csv_path
        )

    logger.info(f"입력 데이터 전처리... ({csv_path})")
    
    # 최적화된 데이터 로딩 사용
    keypoints = optimize_data_loading(csv_path)
    tensor = torch.tensor(keypoints).unsqueeze(0)
    
    logger.info("전처리 완료!")
    return tensor


def predict(
    service: SignLanguageInferenceService, 
    data_tensor: torch.Tensor, 
    vocab_wrapper: Any, 
    device: torch.device
) -> str:
    """
    전처리된 데이터를 배포 모델에 입력하여 예측 결과를 반환합니다.

    Parameters:
        service: 배포 모델 추론 서비스
        data_tensor: 입력 텐서 (1, seq_len, feat_dim)
        vocab_wrapper: 어휘 사전 래퍼
        device: 실행 디바이스

    Returns:
        예측된 단어 문자열
    """
    logger.info("배포 모델 추론 수행...")
    
    # 텐서를 numpy 배열로 변환
    keypoints = data_tensor.squeeze(0).detach().cpu().numpy()  # (seq_len, feat_dim)
    
    # 배포 모델로 예측
    predicted_word = service.predict(keypoints, return_probabilities=False)
    
    logger.info("추론 완료!")
    return predicted_word


def normalize_keypoints_by_bodypart(
    keypoints: np.ndarray,
    width: float = 1.0,
    height: float = 1.0,
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
    bbox_padding: float = BBOX_PADDING
) -> np.ndarray:
    """
    신체 부위별 차별화된 정규화 적용
    
    Args:
        keypoints: (137, 3) 형태의 키포인트 배열 (x, y, confidence)
        width: 프레임 가로 해상도 (기본값 1.0: 이미 정규화된 경우)
        height: 프레임 세로 해상도 (기본값 1.0: 이미 정규화된 경우)
        confidence_threshold: 유효한 키포인트 판별 임계값
        bbox_padding: 바운딩 박스 패딩 비율
        
    Returns:
        정규화된 키포인트 배열 (137, 3)
        
    Keypoint 구조:
    - Pose (0-24): 25개 포즈 키포인트
    - Face (25-94): 70개 얼굴 키포인트
    - Left Hand (95-115): 21개 왼손 키포인트
    - Right Hand (116-136): 21개 오른손 키포인트
    """
    normalized = keypoints.copy()
    
    # === 1. Pose: 전체 화면 기준 정규화 (기존 방식 유지) ===
    pose_kps = keypoints[0:25]
    if width > 1.0:  # 정규화가 필요한 경우만
        normalized[0:25, 0] = pose_kps[:, 0] / width
        normalized[0:25, 1] = pose_kps[:, 1] / height
    
    # === 2. Face: 얼굴 바운딩 박스 기준 정규화 ===
    face_kps = keypoints[25:95]
    face_valid = face_kps[:, 2] > confidence_threshold
    
    if face_valid.sum() >= 5:  # 최소 5개 이상 감지되어야 신뢰 가능
        valid_face = face_kps[face_valid]
        face_x_min, face_x_max = valid_face[:, 0].min(), valid_face[:, 0].max()
        face_y_min, face_y_max = valid_face[:, 1].min(), valid_face[:, 1].max()
        
        # 바운딩 박스에 패딩 추가
        face_w = max(face_x_max - face_x_min, 1e-6)
        face_h = max(face_y_max - face_y_min, 1e-6)
        face_x_min -= face_w * bbox_padding
        face_y_min -= face_h * bbox_padding
        face_w *= (1.0 + 2 * bbox_padding)
        face_h *= (1.0 + 2 * bbox_padding)
        
        # 정규화: 얼굴 영역을 [0, 1] 범위로 확장
        normalized[25:95, 0] = (face_kps[:, 0] - face_x_min) / face_w
        normalized[25:95, 1] = (face_kps[:, 1] - face_y_min) / face_h
    else:
        # 얼굴 감지 실패 시 전체 화면 기준 (fallback)
        if width > 1.0:
            normalized[25:95, 0] = face_kps[:, 0] / width
            normalized[25:95, 1] = face_kps[:, 1] / height
    
    # === 3. Left Hand: 왼손 바운딩 박스 기준 정규화 ===
    left_hand_kps = keypoints[95:116]
    left_hand_valid = left_hand_kps[:, 2] > confidence_threshold
    
    if left_hand_valid.sum() >= 5:
        valid_left = left_hand_kps[left_hand_valid]
        lh_x_min, lh_x_max = valid_left[:, 0].min(), valid_left[:, 0].max()
        lh_y_min, lh_y_max = valid_left[:, 1].min(), valid_left[:, 1].max()
        
        lh_w = max(lh_x_max - lh_x_min, 1e-6)
        lh_h = max(lh_y_max - lh_y_min, 1e-6)
        lh_x_min -= lh_w * bbox_padding
        lh_y_min -= lh_h * bbox_padding
        lh_w *= (1.0 + 2 * bbox_padding)
        lh_h *= (1.0 + 2 * bbox_padding)
        
        normalized[95:116, 0] = (left_hand_kps[:, 0] - lh_x_min) / lh_w
        normalized[95:116, 1] = (left_hand_kps[:, 1] - lh_y_min) / lh_h
    else:
        # 왼손 감지 실패 시 전체 화면 기준
        if width > 1.0:
            normalized[95:116, 0] = left_hand_kps[:, 0] / width
            normalized[95:116, 1] = left_hand_kps[:, 1] / height
    
    # === 4. Right Hand: 오른손 바운딩 박스 기준 정규화 ===
    right_hand_kps = keypoints[116:137]
    right_hand_valid = right_hand_kps[:, 2] > confidence_threshold
    
    if right_hand_valid.sum() >= 5:
        valid_right = right_hand_kps[right_hand_valid]
        rh_x_min, rh_x_max = valid_right[:, 0].min(), valid_right[:, 0].max()
        rh_y_min, rh_y_max = valid_right[:, 1].min(), valid_right[:, 1].max()
        
        rh_w = max(rh_x_max - rh_x_min, 1e-6)
        rh_h = max(rh_y_max - rh_y_min, 1e-6)
        rh_x_min -= rh_w * bbox_padding
        rh_y_min -= rh_h * bbox_padding
        rh_w *= (1.0 + 2 * bbox_padding)
        rh_h *= (1.0 + 2 * bbox_padding)
        
        normalized[116:137, 0] = (right_hand_kps[:, 0] - rh_x_min) / rh_w
        normalized[116:137, 1] = (right_hand_kps[:, 1] - rh_y_min) / rh_h
    else:
        # 오른손 감지 실패 시 전체 화면 기준
        if width > 1.0:
            normalized[116:137, 0] = right_hand_kps[:, 0] / width
            normalized[116:137, 1] = right_hand_kps[:, 1] / height
    
    return normalized
