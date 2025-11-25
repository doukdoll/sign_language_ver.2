"""
KSLT 프로젝트 성능 최적화 유틸리티
"""

import torch
import numpy as np
from typing import Optional, Union, Tuple
from functools import lru_cache
import time
from contextlib import contextmanager
from utils.logger import get_logger

logger = get_logger("kslt.performance")


class PerformanceOptimizer:
    """성능 최적화 도구 클래스"""
    
    def __init__(self, device: Optional[torch.device] = None):
        self.device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._memory_stats = {}
    
    @contextmanager
    def memory_monitor(self, operation_name: str):
        """메모리 사용량 모니터링 컨텍스트 매니저"""
        if self.device.type == "cuda":
            torch.cuda.synchronize()
            start_memory = torch.cuda.memory_allocated()
            start_time = time.perf_counter()
        
        try:
            yield
        finally:
            if self.device.type == "cuda":
                torch.cuda.synchronize()
                end_memory = torch.cuda.memory_allocated()
                end_time = time.perf_counter()
                
                memory_used = end_memory - start_memory
                time_elapsed = end_time - start_time
                
                self._memory_stats[operation_name] = {
                    "memory_mb": memory_used / 1024 / 1024,
                    "time_ms": time_elapsed * 1000
                }
                
                logger.debug(f"{operation_name}: {memory_used/1024/1024:.2f}MB, {time_elapsed*1000:.2f}ms")
    
    def get_memory_stats(self) -> dict:
        """메모리 사용량 통계 반환"""
        return self._memory_stats.copy()
    
    def clear_memory_stats(self) -> None:
        """메모리 통계 초기화"""
        self._memory_stats.clear()


@lru_cache(maxsize=128)
def cached_normalize_keypoints(keypoints_tuple: tuple, method: str = "nose_relative") -> np.ndarray:
    """
    키포인트 정규화 결과 캐싱
    
    Args:
        keypoints_tuple: 키포인트 튜플 (해시 가능한 형태)
        method: 정규화 방법
        
    Returns:
        정규화된 키포인트 배열
    """
    keypoints = np.array(keypoints_tuple).reshape(-1, 2)
    
    if method == "nose_relative":
        # 코 기준 상대 좌표 변환
        nose_point = keypoints[0] if len(keypoints) > 0 else np.array([0, 0])
        normalized = keypoints - nose_point
    else:
        normalized = keypoints
    
    return normalized


def optimize_tensor_operations(tensor: torch.Tensor, inplace: bool = True) -> torch.Tensor:
    """
    텐서 연산 최적화
    
    Args:
        tensor: 최적화할 텐서
        inplace: 인플레이스 연산 사용 여부
        
    Returns:
        최적화된 텐서
    """
    if tensor.is_contiguous():
        return tensor
    
    if inplace:
        return tensor.contiguous()
    else:
        return tensor.clone().contiguous()


def batch_keypoint_processing(
    keypoints_batch: np.ndarray,
    batch_size: int = 32,
    normalize: bool = True
) -> np.ndarray:
    """
    키포인트 배치 처리 최적화
    
    Args:
        keypoints_batch: 키포인트 배치 (N, seq_len, features)
        batch_size: 배치 크기
        normalize: 정규화 여부
        
    Returns:
        처리된 키포인트 배치
    """
    if len(keypoints_batch) <= batch_size:
        return keypoints_batch
    
    # 배치 단위로 처리
    processed_batches = []
    for i in range(0, len(keypoints_batch), batch_size):
        batch = keypoints_batch[i:i + batch_size]
        
        if normalize:
            # 배치 내 모든 시퀀스에 대해 정규화
            for j in range(len(batch)):
                if len(batch[j]) > 0:
                    nose_point = batch[j][0, :2] if batch[j].shape[1] >= 2 else np.array([0, 0])
                    batch[j][:, :2] -= nose_point
        
        processed_batches.append(batch)
    
    return np.concatenate(processed_batches, axis=0)


def memory_efficient_inference(
    model: torch.nn.Module,
    input_tensor: torch.Tensor,
    batch_size: int = 16
) -> torch.Tensor:
    """
    메모리 효율적인 추론
    
    Args:
        model: 추론할 모델
        input_tensor: 입력 텐서
        batch_size: 배치 크기
        
    Returns:
        추론 결과
    """
    if len(input_tensor) <= batch_size:
        with torch.no_grad():
            return model(input_tensor)
    
    # 배치 단위로 추론
    results = []
    for i in range(0, len(input_tensor), batch_size):
        batch = input_tensor[i:i + batch_size]
        with torch.no_grad():
            batch_result = model(batch)
        results.append(batch_result)
        
        # 메모리 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    
    return torch.cat(results, dim=0)


def precompute_attention_weights(
    seq_len: int,
    hidden_size: int,
    num_heads: int = 8
) -> torch.Tensor:
    """
    어텐션 가중치 사전 계산
    
    Args:
        seq_len: 시퀀스 길이
        hidden_size: 히든 크기
        num_heads: 어텐션 헤드 수
        
    Returns:
        사전 계산된 어텐션 가중치
    """
    # 위치 인코딩 사전 계산
    position = torch.arange(seq_len).unsqueeze(1).float()
    div_term = torch.exp(torch.arange(0, hidden_size, 2).float() * 
                        -(np.log(10000.0) / hidden_size))
    
    pe = torch.zeros(seq_len, hidden_size)
    pe[:, 0::2] = torch.sin(position * div_term)
    pe[:, 1::2] = torch.cos(position * div_term)
    
    return pe


def optimize_data_loading(
    data_path: str,
    cache_size: int = 1000
) -> np.ndarray:
    """
    데이터 로딩 최적화
    
    Args:
        data_path: 데이터 파일 경로
        cache_size: 캐시 크기
        
    Returns:
        로드된 데이터
    """
    # 간단한 캐싱 구현
    if not hasattr(optimize_data_loading, '_cache'):
        optimize_data_loading._cache = {}
    
    if data_path in optimize_data_loading._cache:
        return optimize_data_loading._cache[data_path]
    
    # 데이터 로딩
    import pandas as pd
    data = pd.read_csv(data_path).values.astype(np.float32)
    
    # 캐시 크기 제한
    if len(optimize_data_loading._cache) >= cache_size:
        # 가장 오래된 항목 제거
        oldest_key = next(iter(optimize_data_loading._cache))
        del optimize_data_loading._cache[oldest_key]
    
    optimize_data_loading._cache[data_path] = data
    return data


def profile_function(func):
    """함수 실행 시간 프로파일링 데코레이터"""
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        
        logger.debug(f"{func.__name__} 실행 시간: {(end_time - start_time) * 1000:.2f}ms")
        return result
    
    return wrapper


# 전역 성능 최적화 인스턴스
performance_optimizer = PerformanceOptimizer()
