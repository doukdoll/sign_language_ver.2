"""
KSLT 프로젝트 설정 관리 모듈
"""

import yaml
import os
from typing import Dict, Any, Optional
from pathlib import Path
from utils.logger import get_logger
from utils.exceptions import ConfigurationError

logger = get_logger("kslt.config")


class ConfigManager:
    """설정 파일 관리 클래스"""
    
    def __init__(self, config_path: str):
        """
        설정 관리자 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config_path = Path(config_path)
        self._config: Optional[Dict[str, Any]] = None
        self._load_config()
    
    def _load_config(self) -> None:
        """설정 파일 로딩"""
        try:
            if not self.config_path.exists():
                raise ConfigurationError(
                    f"설정 파일을 찾을 수 없습니다: {self.config_path}",
                    config_path=str(self.config_path)
                )
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            if self._config is None:
                raise ConfigurationError(
                    "설정 파일이 비어있거나 유효하지 않습니다",
                    config_path=str(self.config_path)
                )
            
            logger.info(f"설정 파일 로딩 완료: {self.config_path}")
            
        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"YAML 파싱 오류: {e}",
                config_path=str(self.config_path)
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"설정 파일 로딩 실패: {e}",
                config_path=str(self.config_path)
            )
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        설정 값 조회 (점 표기법 지원)
        
        Args:
            key: 설정 키 (예: "model.path", "realtime.window_size")
            default: 기본값
            
        Returns:
            설정 값
        """
        if self._config is None:
            return default
        
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_model_config(self) -> Dict[str, Any]:
        """모델 설정 반환"""
        return self.get('model', {})
    
    def get_realtime_config(self) -> Dict[str, Any]:
        """실시간 처리 설정 반환"""
        return self.get('realtime', {})
    
    def get_segmenter_config(self) -> Dict[str, Any]:
        """세그멘테이션 설정 반환"""
        return self.get('segmenter', {})
    
    def get_logging_config(self) -> Dict[str, Any]:
        """로깅 설정 반환"""
        return self.get('logging', {})
    
    def get_data_config(self) -> Dict[str, Any]:
        """데이터 저장 설정 반환"""
        return self.get('data', {})
    
    def get_visualization_config(self) -> Dict[str, Any]:
        """시각화 설정 반환"""
        return self.get('visualization', {})
    
    def update(self, key: str, value: Any) -> None:
        """
        설정 값 업데이트 (점 표기법 지원)
        
        Args:
            key: 설정 키
            value: 새로운 값
        """
        if self._config is None:
            return
        
        keys = key.split('.')
        config = self._config
        
        # 중간 키들 생성
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # 마지막 키에 값 설정
        config[keys[-1]] = value
        logger.debug(f"설정 업데이트: {key} = {value}")
    
    def save(self, output_path: Optional[str] = None) -> None:
        """
        설정을 파일로 저장
        
        Args:
            output_path: 출력 파일 경로 (None이면 원본 파일에 저장)
        """
        if self._config is None:
            logger.error("저장할 설정이 없습니다.")
            return
        
        save_path = Path(output_path) if output_path else self.config_path
        
        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            logger.info(f"설정 저장 완료: {save_path}")
        except Exception as e:
            logger.error(f"설정 저장 실패: {e}")
            raise
    
    def reload(self) -> None:
        """설정 파일 재로딩"""
        self._load_config()
    
    @property
    def config(self) -> Dict[str, Any]:
        """전체 설정 딕셔너리 반환"""
        return self._config or {}


def load_config(config_path: str) -> ConfigManager:
    """
    설정 파일 로딩 헬퍼 함수
    
    Args:
        config_path: 설정 파일 경로
        
    Returns:
        ConfigManager 인스턴스
    """
    return ConfigManager(config_path)


def get_default_config_path() -> str:
    """기본 설정 파일 경로 반환"""
    return "config/realtime_config.yaml"
