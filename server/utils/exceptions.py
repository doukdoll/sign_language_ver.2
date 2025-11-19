"""
KSLT 프로젝트 커스텀 예외 클래스들
"""

from typing import Optional


class KSLTBaseException(Exception):
    """KSLT 프로젝트 기본 예외 클래스"""
    
    def __init__(self, message: str, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ModelLoadingError(KSLTBaseException):
    """모델 로딩 실패 시 발생하는 예외"""
    
    def __init__(self, message: str, model_path: Optional[str] = None, error_code: str = "MODEL_LOADING_FAILED"):
        super().__init__(message, error_code)
        self.model_path = model_path


class VocabularyError(KSLTBaseException):
    """어휘 사전 관련 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, vocab_path: Optional[str] = None, error_code: str = "VOCABULARY_ERROR"):
        super().__init__(message, error_code)
        self.vocab_path = vocab_path


class CameraError(KSLTBaseException):
    """카메라 관련 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, camera_index: Optional[int] = None, error_code: str = "CAMERA_ERROR"):
        super().__init__(message, error_code)
        self.camera_index = camera_index


class ConfigurationError(KSLTBaseException):
    """설정 파일 관련 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, config_path: Optional[str] = None, error_code: str = "CONFIG_ERROR"):
        super().__init__(message, error_code)
        self.config_path = config_path


class DataProcessingError(KSLTBaseException):
    """데이터 처리 중 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, data_path: Optional[str] = None, error_code: str = "DATA_PROCESSING_ERROR"):
        super().__init__(message, error_code)
        self.data_path = data_path


class InferenceError(KSLTBaseException):
    """추론 과정에서 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, input_shape: Optional[tuple] = None, error_code: str = "INFERENCE_ERROR"):
        super().__init__(message, error_code)
        self.input_shape = input_shape


class SegmentationError(KSLTBaseException):
    """세그멘테이션 과정에서 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, error_code: str = "SEGMENTATION_ERROR"):
        super().__init__(message, error_code)


class ValidationError(KSLTBaseException):
    """데이터 검증 실패 시 발생하는 예외"""
    
    def __init__(self, message: str, validation_type: Optional[str] = None, error_code: str = "VALIDATION_ERROR"):
        super().__init__(message, error_code)
        self.validation_type = validation_type


class DeviceError(KSLTBaseException):
    """디바이스 관련 오류 시 발생하는 예외"""
    
    def __init__(self, message: str, device: Optional[str] = None, error_code: str = "DEVICE_ERROR"):
        super().__init__(message, error_code)
        self.device = device
