import numpy as np
from typing import Optional, Tuple, Union
from utils.logger import get_logger

logger = get_logger("kslt.segmenter")


def hand_speed(prev_lh: Optional[np.ndarray], prev_rh: Optional[np.ndarray], lh: Optional[np.ndarray], rh: Optional[np.ndarray]) -> float:
    """
    손 키포인트의 프레임 간 변화를 이용해 간단한 속도 스칼라를 계산합니다.
    prev_lh, prev_rh, lh, rh: (21, 3) 형태, x/y만 사용
    """
    v = 0.0
    if prev_lh is not None and prev_rh is not None and lh is not None and rh is not None:
        pl = np.nan_to_num(prev_lh[:, :2], nan=0.0, posinf=0.0, neginf=0.0)  # 이전 왼손
        pr = np.nan_to_num(prev_rh[:, :2], nan=0.0, posinf=0.0, neginf=0.0)  # 이전 오른손
        cl = np.nan_to_num(lh[:, :2], nan=0.0, posinf=0.0, neginf=0.0)      # 현재 왼손
        cr = np.nan_to_num(rh[:, :2], nan=0.0, posinf=0.0, neginf=0.0)      # 현재 오른손
        dl = np.linalg.norm((cl - pl).reshape(-1))  # 왼손 이동 거리
        dr = np.linalg.norm((cr - pr).reshape(-1))  # 오른손 이동 거리
        v = float(dl + dr)  # 총 이동 거리
    return v


class OnlineSegmenter:
    """
    실시간 제스처 경계 검출기
    속도(모션)와 모델 확률을 융합하여 수어 단어 방출 시점을 결정
    """

    def __init__(
        self,
        prob_thr: float = 0.55,        # 모델 예측 확률 임계값
        fuse_tau: float = 0.58,        # 속도+확률 융합 임계값
        min_on: int = 5,               # 연속 조건 만족 프레임 수
        cooldown: int = 12,            # 방출 후 대기 프레임 (중복 방지)
        w_motion: float = 0.6,         # 융합 시 속도 가중치
        w_prob: float = 0.4,           # 융합 시 확률 가중치
        blank_id: Optional[int] = None,  # 무의미 동작 라벨 ID
        rearm_tau: float = 0.35,       # 재무장 임계값
        rearm_off: int = 8,            # 재무장 대기 프레임 (동일 단어 재인식용)
    ) -> None:
        self.prob_thr = prob_thr
        self.fuse_tau = fuse_tau
        self.min_on = min_on
        self.cooldown = cooldown
        self.w_motion = w_motion
        self.w_prob = w_prob
        self.blank_id = blank_id
        self.rearm_tau = rearm_tau
        self.rearm_off = rearm_off

        # 내부 상태 (온라인 속도 통계 및 카운터)
        self._speed_mu = 0.0  # 속도 평균
        self._speed_m2 = 0.0  # 속도 분산 계산용
        self._count = 0       # 전체 프레임 수
        self._on_count = 0    # 조건 만족 연속 카운터
        self._cool = 0        # 쿨다운 카운터
        self._last_label: Optional[int] = None  # 마지막 방출 라벨
        self._off_count = 0   # 비활성 상태 카운터

    def _update_speed_stats(self, x: float) -> None:
        """Welford 알고리즘으로 온라인 평균/분산 계산 (속도 정규화용)"""
        self._count += 1
        delta = x - self._speed_mu
        self._speed_mu += delta / self._count
        delta2 = x - self._speed_mu
        self._speed_m2 += delta * delta2

    def _speed_stats(self) -> Tuple[float, float]:
        """속도 통계 반환 (평균, 분산)"""
        if self._count < 2:
            return 0.0, 1e-6
        var = self._speed_m2 / (self._count - 1)
        return self._speed_mu, float(max(var, 1e-12))

    def update(self, probs: np.ndarray, speed: float) -> Optional[int]:
        """
        매 프레임마다 호출되어 방출 여부를 결정합니다.
        
        Parameters:
            probs: (V,) 모델의 softmax 확률 분포
            speed: 손 이동 거리 (스칼라)
            
        Returns:
            방출할 라벨 ID (없으면 None)
        """
        # === 1. 속도 정규화 (z-score 기반 모션 스코어 계산) ===
        self._update_speed_stats(speed)
        mu, var = self._speed_stats()
        sigma = float(np.sqrt(var))
        if sigma < 1e-6:
            motion_score = 0.0
        else:
            z = (speed - mu) / (3.0 * sigma)  # z-score 계산
            motion_score = float(np.clip(0.5 + z, 0.0, 1.0))  # 0~1 정규화

        # === 2. 모델 확률에서 최대값과 라벨 추출 ===
        max_p = float(probs.max())  # 가장 높은 확률
        label = int(probs.argmax())  # 가장 높은 확률의 라벨 ID

        # Blank 라벨이면 확률을 0으로 강제 (무의미 동작 필터링)
        if self.blank_id is not None and label == self.blank_id:
            max_p = 0.0

        # === 3. 속도와 확률 융합 ===
        fused = self.w_motion * motion_score + self.w_prob * max_p
        
        # 디버깅 출력: 융합 점수 계산 과정
        logger.debug(f"모션: {motion_score:.3f}, 확률: {max_p:.3f}, 융합: {fused:.3f}, 임계값: {self.fuse_tau:.3f}")

        # === 4. ON 카운터 업데이트 (조건 만족 시 증가) ===
        if fused > self.fuse_tau and max_p > self.prob_thr:
            self._on_count += 1  # 조건 만족: 카운터 증가
        else:
            self._on_count = 0   # 조건 불만족: 리셋

        # === 5. OFF 카운터 및 재무장 처리 ===
        if fused < self.rearm_tau or (self.blank_id is not None and label == self.blank_id):
            # Blank이거나 융합값이 낮으면 OFF 카운터 증가
            self._off_count += 2 if (self.blank_id is not None and label == self.blank_id) else 1
        else:
            self._off_count = 0

        if self._off_count >= self.rearm_off:
            # 충분히 쉬면 동일 라벨도 재인식 가능하도록 재무장
            self._last_label = None
            self._off_count = 0

        # === 6. 방출 결정 ===
        emit: Optional[int] = None
        if self._on_count >= self.min_on and self._cool == 0:
            # 조건: ON 카운터가 임계값 이상 & 쿨다운이 0
            if label != self._last_label:  # 이전 라벨과 다르면
                emit = label  # 방출!
                logger.info(f"라벨 {label} 방출! (ON: {self._on_count}, 쿨다운: {self._cool})")
                self._last_label = label
                self._cool = self.cooldown  # 쿨다운 시작
            self._on_count = 0

        if self._cool > 0:
            self._cool -= 1  # 쿨다운 감소

        return emit  # None 또는 라벨 ID 반환


