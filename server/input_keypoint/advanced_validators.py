"""
고급 검증 시스템 (Advanced Validators)
Sign-Language-project 방법론: 단계적 적용을 위한 추가 검증 기능

이 파일은 향후 통합을 위해 준비되었으며, 현재는 통합되지 않은 상태입니다.
통합하려면 이 모듈을 import하고
원하는 검증 메서드를 호출하면 됩니다.

사용 예시:
    from input_keypoint.advanced_validators import AdvancedHandValidator
    
    validator = AdvancedHandValidator()
    
    # 머리 겹침 체크
    if not validator.check_head_occlusion(keypoints):
        print("머리 겹침 감지 - 프레임 제외")
    
    # 도메인 검증
    validation_result = validator.validate_sequence(keypoints_sequence)
    if not validation_result['is_valid']:
        print(f"검증 실패: {validation_result['issues']}")
"""

import numpy as np
from typing import Dict, List, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class AdvancedHandValidator:
    """
    고급 수어 검증 시스템
    (Sign-Language-project 방법론: 단계적 적용)
    
    이 클래스는 다음 기능을 제공합니다:
    1. 머리 겹침 체크 (Head Occlusion Detection)
    2. 도메인 지식 기반 시퀀스 검증 (Domain Knowledge Validation)
    """
    
    # OpenPose BODY_25 키포인트 인덱스
    NOSE_IDX = 0          # 코 (머리 대표점)
    NECK_IDX = 1          # 목
    MID_HIP_IDX = 8       # 허리 중앙
    POSE_KEYPOINTS = 25
    FACE_KEYPOINTS = 70
    HAND_KEYPOINTS = 21
    LEFT_HAND_START = POSE_KEYPOINTS + FACE_KEYPOINTS  # 95
    RIGHT_HAND_START = LEFT_HAND_START + HAND_KEYPOINTS  # 116
    
    def __init__(self,
                 head_occlusion_threshold: float = 0.8,
                 min_hand_movement: float = 10.0,
                 max_frame_gap: int = 5,
                 min_valid_frames_ratio: float = 0.6):
        """
        고급 검증 시스템 초기화
        
        Args:
            head_occlusion_threshold: 머리 위에 있는 손 비율 임계값 (0.8 = 80%)
            min_hand_movement: 최소 손 이동 거리 (픽셀 또는 정규화된 단위)
            max_frame_gap: 최대 프레임 간격 (연속성 체크)
            min_valid_frames_ratio: 최소 유효 프레임 비율 (0.6 = 60%)
        """
        self.head_occlusion_threshold = head_occlusion_threshold
        self.min_hand_movement = min_hand_movement
        self.max_frame_gap = max_frame_gap
        self.min_valid_frames_ratio = min_valid_frames_ratio
        
        logger.info(f"AdvancedHandValidator 초기화:")
        logger.info(f"  - 머리 겹침 임계값: {head_occlusion_threshold * 100}%")
        logger.info(f"  - 최소 손 이동: {min_hand_movement}")
        logger.info(f"  - 최대 프레임 간격: {max_frame_gap}")
        logger.info(f"  - 최소 유효 프레임 비율: {min_valid_frames_ratio * 100}%")
    
    def check_head_occlusion(self, keypoints: np.ndarray) -> bool:
        """
        손이 머리 위에 있는 비정상 상황 감지
        (오검출 또는 포즈 추정 오류)
        
        Args:
            keypoints: (total_keypoints, 3) 형태의 키포인트 배열 (x, y, confidence)
        
        Returns:
            정상이면 True, 오검출이면 False
        """
        # 머리 대표점 (코) y좌표
        head_y = keypoints[self.NOSE_IDX, 1]
        head_conf = keypoints[self.NOSE_IDX, 2]
        
        # 머리 키포인트가 유효하지 않으면 검증 불가 (기본 통과)
        if head_conf <= 0:
            return True
        
        # 양손 키포인트
        left_hand_keypoints = keypoints[self.LEFT_HAND_START:self.RIGHT_HAND_START, :]
        right_hand_keypoints = keypoints[self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, :]
        
        left_hand_y = left_hand_keypoints[:, 1]
        left_hand_conf = left_hand_keypoints[:, 2]
        
        right_hand_y = right_hand_keypoints[:, 1]
        right_hand_conf = right_hand_keypoints[:, 2]
        
        # 신뢰도가 있는 키포인트만 필터링
        valid_left_y = left_hand_y[left_hand_conf > 0]
        valid_right_y = right_hand_y[right_hand_conf > 0]
        
        # 오른손의 대부분(임계값 이상)이 머리 위에 있으면 오류
        if len(valid_right_y) > 0:
            right_above_head_count = np.sum(valid_right_y < head_y)
            right_above_head_ratio = right_above_head_count / len(valid_right_y)
            
            if right_above_head_ratio > self.head_occlusion_threshold:
                logger.debug(f"오른손 머리 겹침 감지: {right_above_head_ratio * 100:.1f}% > {self.head_occlusion_threshold * 100}%")
                return False  # 오검출
        
        # 왼손도 체크
        if len(valid_left_y) > 0:
            left_above_head_count = np.sum(valid_left_y < head_y)
            left_above_head_ratio = left_above_head_count / len(valid_left_y)
            
            if left_above_head_ratio > self.head_occlusion_threshold:
                logger.debug(f"왼손 머리 겹침 감지: {left_above_head_ratio * 100:.1f}% > {self.head_occlusion_threshold * 100}%")
                return False  # 오검출
        
        return True  # 정상
    
    def _calculate_hand_movement(self, sequence: np.ndarray) -> Tuple[float, float]:
        """
        손의 총 이동 거리 계산
        
        Args:
            sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
        
        Returns:
            (left_hand_movement, right_hand_movement) - 각 손의 총 이동 거리
        """
        frames = sequence.shape[0]
        
        if frames < 2:
            return 0.0, 0.0
        
        # 왼손 키포인트 (x, y만 사용)
        left_hand = sequence[:, self.LEFT_HAND_START:self.RIGHT_HAND_START, :2]  # (frames, 21, 2)
        right_hand = sequence[:, self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, :2]
        
        # 각 손의 중심점 계산 (평균)
        with np.errstate(invalid='ignore'):  # NaN 경고 무시
            left_center = np.nanmean(left_hand, axis=1)  # (frames, 2)
            right_center = np.nanmean(right_hand, axis=1)
        
        # 프레임 간 이동 거리 계산
        left_diffs = np.diff(left_center, axis=0)  # (frames-1, 2)
        right_diffs = np.diff(right_center, axis=0)
        
        # 유클리드 거리로 변환하고 합산
        left_distances = np.linalg.norm(left_diffs, axis=1)  # (frames-1,)
        right_distances = np.linalg.norm(right_diffs, axis=1)
        
        # NaN을 제거하고 합산
        left_movement = np.nansum(left_distances)
        right_movement = np.nansum(right_distances)
        
        return float(left_movement), float(right_movement)
    
    def _check_hand_presence(self, sequence: np.ndarray) -> np.ndarray:
        """
        각 프레임에서 손이 감지되었는지 체크
        
        Args:
            sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
        
        Returns:
            (frames,) 형태의 boolean 배열 (True = 손 감지됨)
        """
        frames = sequence.shape[0]
        presence = np.zeros(frames, dtype=bool)
        
        for i in range(frames):
            frame = sequence[i]
            
            # confidence가 있는 경우
            if frame.shape[1] >= 3:
                left_hand_conf = frame[self.LEFT_HAND_START:self.RIGHT_HAND_START, 2]
                right_hand_conf = frame[self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, 2]
                
                # 적어도 한 손에 유효한 키포인트가 있으면 True
                presence[i] = (np.any(left_hand_conf > 0) or np.any(right_hand_conf > 0))
            else:
                # confidence 정보가 없으면 NaN이 아닌 값이 있는지로 판단
                left_hand_xy = frame[self.LEFT_HAND_START:self.RIGHT_HAND_START, :2]
                right_hand_xy = frame[self.RIGHT_HAND_START:self.RIGHT_HAND_START + self.HAND_KEYPOINTS, :2]
                
                presence[i] = (np.any(~np.isnan(left_hand_xy)) or np.any(~np.isnan(right_hand_xy)))
        
        return presence
    
    def _find_gaps(self, presence: np.ndarray) -> List[int]:
        """
        연속된 False (손 미감지) 구간의 길이들을 찾음
        
        Args:
            presence: (frames,) 형태의 boolean 배열
        
        Returns:
            각 gap의 길이 리스트
        """
        gaps = []
        current_gap = 0
        
        for p in presence:
            if not p:
                current_gap += 1
            else:
                if current_gap > 0:
                    gaps.append(current_gap)
                    current_gap = 0
        
        # 마지막 gap 추가
        if current_gap > 0:
            gaps.append(current_gap)
        
        return gaps
    
    def validate_sequence(self, keypoints_sequence: np.ndarray, skip_head_occlusion: bool = True) -> Dict[str, Any]:
        """
        시퀀스 전체에 대한 도메인 지식 기반 검증
        
        Args:
            keypoints_sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
            skip_head_occlusion: True이면 머리 겹침 체크를 건너뜀
        
        Returns:
            검증 결과 딕셔너리:
            {
                'is_valid': bool,
                'issues': List[str],
                'quality_score': float (0.0 ~ 1.0),
                'details': Dict[str, Any]
            }
        """
        results = {
            'is_valid': True,
            'issues': [],
            'quality_score': 1.0,
            'details': {}
        }
        
        frames = keypoints_sequence.shape[0]
        
        # 1. 손 움직임 체크
        left_movement, right_movement = self._calculate_hand_movement(keypoints_sequence)
        max_movement = max(left_movement, right_movement)
        
        results['details']['left_hand_movement'] = left_movement
        results['details']['right_hand_movement'] = right_movement
        results['details']['max_hand_movement'] = max_movement
        
        if max_movement < self.min_hand_movement:
            results['issues'].append('insufficient_hand_movement')
            results['quality_score'] *= 0.7
            logger.debug(f"손 움직임 부족: {max_movement:.2f} < {self.min_hand_movement}")
        
        # 2. 유효 프레임 비율 체크
        hand_presence = self._check_hand_presence(keypoints_sequence)
        valid_frames_count = np.sum(hand_presence)
        valid_ratio = valid_frames_count / frames
        
        results['details']['valid_frames_count'] = int(valid_frames_count)
        results['details']['total_frames'] = frames
        results['details']['valid_ratio'] = valid_ratio
        
        if valid_ratio < self.min_valid_frames_ratio:
            results['issues'].append('low_valid_frame_ratio')
            results['quality_score'] *= 0.5
            results['is_valid'] = False
            logger.debug(f"유효 프레임 비율 낮음: {valid_ratio:.2%} < {self.min_valid_frames_ratio:.2%}")
        
        # 3. 연속성 체크 (손이 갑자기 사라지면 의심)
        gaps = self._find_gaps(hand_presence)
        max_gap = max(gaps) if gaps else 0
        
        results['details']['gaps'] = gaps
        results['details']['max_gap'] = max_gap
        
        if max_gap > self.max_frame_gap:
            results['issues'].append('discontinuous_hand_tracking')
            results['quality_score'] *= 0.8
            logger.debug(f"손 추적 불연속: 최대 gap {max_gap} > {self.max_frame_gap}")
        
        # 4. 머리 겹침 체크 (선택적)
        if not skip_head_occlusion:
            occlusion_count = 0
            for i in range(frames):
                frame = keypoints_sequence[i]
                if not self.check_head_occlusion(frame):
                    occlusion_count += 1
            
            occlusion_ratio = occlusion_count / frames
            results['details']['head_occlusion_frames'] = occlusion_count
            results['details']['head_occlusion_ratio'] = occlusion_ratio
            
            if occlusion_ratio > 0.3:  # 30% 이상 오류
                results['issues'].append('high_head_occlusion_rate')
                results['quality_score'] *= 0.6
                logger.debug(f"머리 겹침 비율 높음: {occlusion_ratio:.2%}")
        
        # 최종 품질 점수 클리핑
        results['quality_score'] = max(0.0, min(1.0, results['quality_score']))
        
        logger.info(f"시퀀스 검증 완료: valid={results['is_valid']}, "
                   f"score={results['quality_score']:.2f}, issues={results['issues']}")
        
        return results
    
    def filter_valid_frames(self, keypoints_sequence: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        시퀀스에서 유효한 프레임만 필터링
        
        Args:
            keypoints_sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
        
        Returns:
            (filtered_sequence, valid_indices) - 필터링된 시퀀스와 유효한 프레임 인덱스
        """
        frames = keypoints_sequence.shape[0]
        valid_indices = []
        
        for i in range(frames):
            frame = keypoints_sequence[i]
            
            # 머리 겹침 체크
            if self.check_head_occlusion(frame):
                valid_indices.append(i)
        
        if len(valid_indices) == 0:
            logger.warning("유효한 프레임이 없습니다. 원본 시퀀스를 반환합니다.")
            return keypoints_sequence, np.arange(frames)
        
        valid_indices = np.array(valid_indices)
        filtered_sequence = keypoints_sequence[valid_indices]
        
        logger.info(f"프레임 필터링: {frames}개 -> {len(valid_indices)}개 "
                   f"({len(valid_indices) / frames * 100:.1f}% 유지)")
        
        return filtered_sequence, valid_indices


class HandSignQualityEvaluator:
    """
    수어 품질 평가 시스템
    
    시퀀스의 품질을 종합적으로 평가하고 점수화합니다.
    """
    
    def __init__(self):
        self.validator = AdvancedHandValidator()
    
    def evaluate(self, keypoints_sequence: np.ndarray) -> Dict[str, Any]:
        """
        시퀀스의 품질을 종합 평가
        
        Args:
            keypoints_sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
        
        Returns:
            평가 결과 딕셔너리
        """
        validation_result = self.validator.validate_sequence(keypoints_sequence)
        
        # 평가 등급 결정
        score = validation_result['quality_score']
        if score >= 0.9:
            grade = 'A'
        elif score >= 0.8:
            grade = 'B'
        elif score >= 0.7:
            grade = 'C'
        elif score >= 0.6:
            grade = 'D'
        else:
            grade = 'F'
        
        evaluation = {
            **validation_result,
            'grade': grade,
            'recommendation': self._get_recommendation(validation_result)
        }
        
        return evaluation
    
    def _get_recommendation(self, validation_result: Dict[str, Any]) -> str:
        """
        검증 결과에 따른 권장사항 생성
        """
        issues = validation_result['issues']
        
        if not issues:
            return "품질이 우수합니다. 학습에 사용하기 적합합니다."
        
        recommendations = []
        
        if 'insufficient_hand_movement' in issues:
            recommendations.append("손 움직임이 부족합니다. 동적인 동작을 포함하는지 확인하세요.")
        
        if 'low_valid_frame_ratio' in issues:
            recommendations.append("유효한 프레임 비율이 낮습니다. 손 검출이 잘 되는 환경에서 촬영하세요.")
        
        if 'discontinuous_hand_tracking' in issues:
            recommendations.append("손 추적이 불연속적입니다. 조명이나 배경을 개선하세요.")
        
        if 'high_head_occlusion_rate' in issues:
            recommendations.append("머리 겹침 오류가 많습니다. 카메라 각도나 포즈 추정 모델을 확인하세요.")
        
        return " ".join(recommendations)


# 편의 함수들
def validate_keypoints_sequence(keypoints_sequence: np.ndarray,
                                min_quality_score: float = 0.6) -> Tuple[bool, Dict[str, Any]]:
    """
    키포인트 시퀀스 검증 (간편 함수)
    
    Args:
        keypoints_sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
        min_quality_score: 최소 품질 점수
    
    Returns:
        (is_valid, validation_result)
    """
    validator = AdvancedHandValidator()
    result = validator.validate_sequence(keypoints_sequence)
    
    is_valid = result['is_valid'] and result['quality_score'] >= min_quality_score
    
    return is_valid, result


def evaluate_keypoints_quality(keypoints_sequence: np.ndarray) -> Dict[str, Any]:
    """
    키포인트 품질 평가 (간편 함수)
    
    Args:
        keypoints_sequence: (frames, total_keypoints, 2 or 3) 형태의 시퀀스
    
    Returns:
        평가 결과 딕셔너리
    """
    evaluator = HandSignQualityEvaluator()
    return evaluator.evaluate(keypoints_sequence)


if __name__ == "__main__":
    # 테스트 코드
    print("=== Advanced Validators 테스트 ===\n")
    
    # 더미 데이터 생성 (180 프레임, 137 키포인트, x/y/confidence)
    dummy_sequence = np.random.rand(180, 137, 3)
    
    # 손 움직임 시뮬레이션 (왼손을 위로 이동)
    for i in range(180):
        # 왼손 (95~115)
        dummy_sequence[i, 95:116, 1] = 0.5 - (i / 180) * 0.3  # y좌표 감소 (위로 이동)
        dummy_sequence[i, 95:116, 2] = 0.8  # 높은 신뢰도
    
    # 검증 실행
    validator = AdvancedHandValidator()
    
    print("1. 머리 겹침 체크 (첫 프레임):")
    result = validator.check_head_occlusion(dummy_sequence[0])
    print(f"   결과: {'정상' if result else '오검출'}\n")
    
    print("2. 시퀀스 전체 검증:")
    validation_result = validator.validate_sequence(dummy_sequence)
    print(f"   유효성: {validation_result['is_valid']}")
    print(f"   품질 점수: {validation_result['quality_score']:.2f}")
    print(f"   이슈: {validation_result['issues']}")
    print(f"   세부정보: {validation_result['details']}\n")
    
    print("3. 품질 평가:")
    evaluator = HandSignQualityEvaluator()
    evaluation = evaluator.evaluate(dummy_sequence)
    print(f"   등급: {evaluation['grade']}")
    print(f"   권장사항: {evaluation['recommendation']}\n")
    
    print("테스트 완료!")

