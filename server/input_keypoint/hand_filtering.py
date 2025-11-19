"""
손 위치 기반 필터링 및 선택적 프레임 증강
Sign-Language-project 방법론 구현

이 모듈은 수어 도메인 지식을 활용하여 데이터 품질을 향상시킵니다:
1. 손 위치 기반 필터링: 손이 허리보다 위에 있는 프레임만 유효한 수어로 판단
2. 선택적 프레임 증강: 손이 명확히 보이는 프레임을 우선적으로 복제

사용 예시:
    from input_keypoint.hand_filtering import HandFilteringProcessor
    
    # 기본 사용
    processor = HandFilteringProcessor()
    
    # 단일 프레임 검증
    is_valid = processor.validate_hand_position(keypoints)
    
    # 선택적 프레임 증강
    augmented = processor.augment_hand_frames(
        keypoints_sequence,
        keypoints_with_conf,
        target_frames=180
    )
"""

import numpy as np
from typing import List
import logging

logger = logging.getLogger(__name__)


class HandFilteringProcessor:
    """
    손 위치 기반 필터링 및 선택적 프레임 증강 프로세서
    (Sign-Language-project 방법론)
    """
    
    # OpenPose BODY_25 키포인트 인덱스
    NOSE_IDX = 0          # 코 (머리 대표점)
    MID_HIP_IDX = 8       # 허리 중앙
    POSE_KEYPOINTS = 25
    FACE_KEYPOINTS = 70
    HAND_KEYPOINTS = 21
    LEFT_HAND_START = POSE_KEYPOINTS + FACE_KEYPOINTS  # 95
    RIGHT_HAND_START = LEFT_HAND_START + HAND_KEYPOINTS  # 116
    
    def __init__(self, hand_confidence_threshold: float = 0.5):
        """
        초기화
        
        Args:
            hand_confidence_threshold: 손 키포인트 신뢰도 임계값 (0.0 ~ 1.0)
        """
        self.hand_confidence_threshold = hand_confidence_threshold
        logger.info(f"HandFilteringProcessor 초기화: 신뢰도 임계값={hand_confidence_threshold}")
    
    def validate_hand_position(self, keypoints: np.ndarray) -> bool:
        """
        수어 도메인 지식 활용: 손이 허리보다 위에 있는지 검증
        
        Args:
            keypoints: (total_keypoints, 3) 형태의 키포인트 배열 (x, y, confidence)
        
        Returns:
            유효한 수어 프레임이면 True, 그렇지 않으면 False
        """
        # 허리 중앙의 y좌표 (정규화된 좌표)
        pelvis_y = keypoints[self.MID_HIP_IDX, 1]
        pelvis_conf = keypoints[self.MID_HIP_IDX, 2]
        
        # 허리 키포인트가 유효하지 않으면 검증 불가 (기본 통과)
        if pelvis_conf <= 0:
            return True
        
        # 왼손 키포인트 (정규화된 좌표)
        left_hand_keypoints = keypoints[self.LEFT_HAND_START:self.RIGHT_HAND_START, :]
        left_hand_y = left_hand_keypoints[:, 1]
        left_hand_conf = left_hand_keypoints[:, 2]
        
        # 오른손 키포인트 (정규화된 좌표)
        right_hand_keypoints = keypoints[self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, :]
        right_hand_y = right_hand_keypoints[:, 1]
        right_hand_conf = right_hand_keypoints[:, 2]
        
        # 신뢰도가 있는 키포인트만 필터링
        valid_left_y = left_hand_y[left_hand_conf > 0]
        valid_right_y = right_hand_y[right_hand_conf > 0]
        
        # 왼손의 평균 y좌표 계산
        left_hand_mean = np.mean(valid_left_y) if len(valid_left_y) > 0 else np.inf
        
        # 오른손의 평균 y좌표 계산
        right_hand_mean = np.mean(valid_right_y) if len(valid_right_y) > 0 else np.inf
        
        # ★ 적어도 한 손이 허리보다 위에 있으면 유효한 수어 프레임
        # (y좌표가 작을수록 위쪽이므로 < 비교)
        if not np.isinf(left_hand_mean) and left_hand_mean < pelvis_y:
            return True
        if not np.isinf(right_hand_mean) and right_hand_mean < pelvis_y:
            return True
        
        return False
    
    def get_hand_confidence_score(self, keypoints: np.ndarray) -> float:
        """
        손 키포인트의 전체 신뢰도 점수 계산
        
        Args:
            keypoints: (total_keypoints, 3) 형태의 키포인트 배열
        
        Returns:
            0.0 ~ 1.0 사이의 신뢰도 점수 (양손 중 높은 쪽)
        """
        # 왼손 신뢰도
        left_hand_conf = keypoints[self.LEFT_HAND_START:self.RIGHT_HAND_START, 2]
        left_conf_mean = np.mean(left_hand_conf[left_hand_conf > 0]) if np.any(left_hand_conf > 0) else 0.0
        
        # 오른손 신뢰도
        right_hand_conf = keypoints[self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, 2]
        right_conf_mean = np.mean(right_hand_conf[right_hand_conf > 0]) if np.any(right_hand_conf > 0) else 0.0
        
        # 양손 중 높은 신뢰도 반환
        return max(left_conf_mean, right_conf_mean)
    
    def filter_valid_frames(self, keypoints_sequence: np.ndarray) -> List[int]:
        """
        시퀀스에서 유효한 프레임 인덱스 찾기
        
        Args:
            keypoints_sequence: (frames, total_keypoints, 3) - x, y, confidence
        
        Returns:
            유효한 프레임 인덱스 리스트
        """
        valid_indices = []
        
        for i in range(len(keypoints_sequence)):
            frame = keypoints_sequence[i]
            
            # 손 위치 검증
            if self.validate_hand_position(frame):
                # 손 신뢰도 체크
                conf_score = self.get_hand_confidence_score(frame)
                if conf_score >= self.hand_confidence_threshold:
                    valid_indices.append(i)
        
        return valid_indices
    
    def augment_hand_frames(self,
                           keypoints_sequence: np.ndarray,
                           keypoints_with_conf: np.ndarray,
                           target_frames: int) -> np.ndarray:
        """
        손이 명확히 보이는 프레임을 선택적으로 증강
        
        Args:
            keypoints_sequence: (original_frames, keypoints, 2) - x, y 좌표
            keypoints_with_conf: (original_frames, keypoints, 3) - x, y, confidence
            target_frames: 목표 프레임 수
        
        Returns:
            증강된 시퀀스: (target_frames, keypoints, 2)
        """
        original_frames = keypoints_sequence.shape[0]
        
        if original_frames >= target_frames:
            # 이미 충분한 프레임이 있으면 그대로 반환
            return keypoints_sequence[:target_frames]
        
        # 1. 손이 유효한 프레임 인덱스 수집
        hand_valid_frames = self.filter_valid_frames(keypoints_with_conf)
        
        # 2. 부족한 프레임 수 계산
        needed = target_frames - original_frames
        
        if len(hand_valid_frames) == 0:
            # 유효한 손 프레임이 없으면 전체에서 균등 샘플링
            logger.warning("유효한 손 프레임이 없습니다. 균등 샘플링을 사용합니다.")
            hand_valid_frames = list(range(original_frames))
        
        # 3. 손이 보이는 프레임을 우선적으로 복제
        augment_indices = np.random.choice(hand_valid_frames, size=needed, replace=True)
        augment_indices.sort()
        
        # 4. 원본 시퀀스에 삽입
        result = list(keypoints_sequence)
        for offset, idx in enumerate(augment_indices):
            insert_pos = idx + offset
            # 원본 프레임 복제
            result.insert(insert_pos, keypoints_sequence[idx].copy())
        
        # 5. 목표 프레임 수로 자르기
        result_array = np.array(result[:target_frames])
        
        logger.debug(f"선택적 프레임 증강: {original_frames} -> {target_frames} "
                    f"(유효 프레임: {len(hand_valid_frames)}개)")
        
        return result_array
    
    def get_statistics(self, keypoints_sequence: np.ndarray) -> dict:
        """
        시퀀스의 통계 정보 반환
        
        Args:
            keypoints_sequence: (frames, total_keypoints, 3) - x, y, confidence
        
        Returns:
            통계 정보 딕셔너리
        """
        total_frames = len(keypoints_sequence)
        valid_frames = self.filter_valid_frames(keypoints_sequence)
        
        # 평균 신뢰도 계산
        confidence_scores = [
            self.get_hand_confidence_score(frame)
            for frame in keypoints_sequence
        ]
        
        return {
            'total_frames': total_frames,
            'valid_frames_count': len(valid_frames),
            'valid_frames_ratio': len(valid_frames) / total_frames if total_frames > 0 else 0.0,
            'valid_frame_indices': valid_frames,
            'avg_confidence': np.mean(confidence_scores),
            'min_confidence': np.min(confidence_scores),
            'max_confidence': np.max(confidence_scores),
        }


def filter_hand_frames(keypoints_sequence: np.ndarray,
                      hand_confidence_threshold: float = 0.5) -> List[int]:
    """
    편의 함수: 유효한 손 프레임 인덱스 찾기
    
    Args:
        keypoints_sequence: (frames, total_keypoints, 3) - x, y, confidence
        hand_confidence_threshold: 손 신뢰도 임계값
    
    Returns:
        유효한 프레임 인덱스 리스트
    """
    processor = HandFilteringProcessor(hand_confidence_threshold)
    return processor.filter_valid_frames(keypoints_sequence)


def augment_with_hand_priority(keypoints_sequence: np.ndarray,
                               keypoints_with_conf: np.ndarray,
                               target_frames: int,
                               hand_confidence_threshold: float = 0.5) -> np.ndarray:
    """
    편의 함수: 손이 보이는 프레임 우선 증강
    
    Args:
        keypoints_sequence: (original_frames, keypoints, 2) - x, y 좌표
        keypoints_with_conf: (original_frames, keypoints, 3) - x, y, confidence
        target_frames: 목표 프레임 수
        hand_confidence_threshold: 손 신뢰도 임계값
    
    Returns:
        증강된 시퀀스: (target_frames, keypoints, 2)
    """
    processor = HandFilteringProcessor(hand_confidence_threshold)
    return processor.augment_hand_frames(
        keypoints_sequence,
        keypoints_with_conf,
        target_frames
    )


if __name__ == "__main__":
    # 테스트 코드
    print("=== Hand Filtering Processor 테스트 ===\n")
    
    # 더미 데이터 생성
    dummy_frames = 150
    dummy_keypoints = 137
    
    # 시퀀스 생성 (x, y, confidence)
    dummy_sequence_with_conf = np.random.rand(dummy_frames, dummy_keypoints, 3)
    dummy_sequence_xy = dummy_sequence_with_conf[:, :, :2]
    
    # 손 움직임 시뮬레이션 (일부 프레임에서 손이 허리보다 위에)
    for i in range(0, dummy_frames, 3):  # 매 3프레임마다
        # 왼손을 허리보다 위로
        dummy_sequence_with_conf[i, 95:116, 1] = 0.3  # y좌표 (위쪽)
        dummy_sequence_with_conf[i, 95:116, 2] = 0.8  # 높은 신뢰도
        
        # 허리 위치
        dummy_sequence_with_conf[i, 8, 1] = 0.5  # 허리 y좌표
        dummy_sequence_with_conf[i, 8, 2] = 0.9  # 허리 신뢰도
    
    # 프로세서 생성
    processor = HandFilteringProcessor(hand_confidence_threshold=0.5)
    
    # 1. 통계 정보
    print("1. 시퀀스 통계:")
    stats = processor.get_statistics(dummy_sequence_with_conf)
    for key, value in stats.items():
        if key != 'valid_frame_indices':
            print(f"   {key}: {value}")
    print()
    
    # 2. 선택적 프레임 증강
    print("2. 선택적 프레임 증강:")
    target = 180
    augmented = processor.augment_hand_frames(
        dummy_sequence_xy,
        dummy_sequence_with_conf,
        target
    )
    print(f"   원본: {dummy_frames} 프레임")
    print(f"   증강 후: {augmented.shape[0]} 프레임")
    print(f"   목표: {target} 프레임")
    print()
    
    # 3. 편의 함수 테스트
    print("3. 편의 함수 테스트:")
    valid_indices = filter_hand_frames(dummy_sequence_with_conf)
    print(f"   유효 프레임 수: {len(valid_indices)}")
    
    print("\n테스트 완료!")

