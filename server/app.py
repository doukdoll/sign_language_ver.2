"""
KSLT 실시간 수어 인식 시스템 메인 엔트리포인트
"""

from utils.logger import setup_project_logging
from utils.config import get_default_config_path
from realtime.app_main import realtime_translation


if __name__ == "__main__":
    # 프로젝트 로깅 설정
    setup_project_logging()
    
    # 기본 설정 파일로 실시간 번역 시작
    config_path = get_default_config_path()
    realtime_translation(config_path)