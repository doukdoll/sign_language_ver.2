"""
KSLT 프로젝트 공통 로깅 설정 모듈
"""

import logging
import sys
from typing import Optional
from pathlib import Path


def setup_logger(
    name: str = "kslt",
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_string: Optional[str] = None
) -> logging.Logger:
    """
    KSLT 프로젝트용 로거를 설정합니다.
    
    Args:
        name: 로거 이름
        level: 로깅 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 로그 파일 경로 (None이면 콘솔만 출력)
        format_string: 로그 포맷 문자열
        
    Returns:
        설정된 로거 객체
    """
    logger = logging.getLogger(name)
    
    # 이미 핸들러가 설정되어 있으면 기존 핸들러 제거
    if logger.handlers:
        logger.handlers.clear()
    
    # 로깅 레벨 설정
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)
    
    # 기본 포맷 설정
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    formatter = logging.Formatter(format_string)
    
    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 추가 (선택사항)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = "kslt") -> logging.Logger:
    """
    기존 로거를 가져오거나 새로 생성합니다.
    
    Args:
        name: 로거 이름
        
    Returns:
        로거 객체
    """
    return logging.getLogger(name)


# 프로젝트 전역 로거 설정
def setup_project_logging(config: Optional[dict] = None) -> logging.Logger:
    """
    프로젝트 전체 로깅을 설정합니다.
    
    Args:
        config: 로깅 설정 딕셔너리
        
    Returns:
        메인 로거 객체
    """
    if config is None:
        config = {
            "level": "INFO",
            "log_file": "logs/kslt.log",
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    
    return setup_logger(
        name="kslt",
        level=config.get("level", "INFO"),
        log_file=config.get("log_file"),
        format_string=config.get("format")
    )
