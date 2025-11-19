"""
배포된 수어 인식 모델을 위한 추론 서비스
PyTorch 및 ONNX 런타임 지원
"""

import os
import torch
import numpy as np
from typing import Optional, Union, Dict, Any, List
import yaml
from utils.logger import get_logger
from utils.exceptions import ModelLoadingError, VocabularyError, InferenceError, DeviceError

logger = get_logger("kslt.inference_service")


class SignLanguageInferenceService:
    """
    배포된 수어 인식 모델을 사용한 추론 서비스
    """
    
    def __init__(
        self,
        model_path: str,
        vocab_path: str,
        device: str = "auto",
        model_type: str = "pytorch"
    ):
        """
        추론 서비스 초기화
        
        Args:
            model_path: 모델 파일 경로 (.pt 또는 .onnx)
            vocab_path: 어휘 사전 파일 경로
            device: 실행 디바이스 ("cuda", "cpu", "auto")
            model_type: 모델 타입 ("pytorch" 또는 "onnx")
        """
        self.model_path = model_path
        self.vocab_path = vocab_path
        self.model_type = model_type.lower()
        
        # 디바이스 설정
        if device == "auto":
            if torch.cuda.is_available():
                self.device = torch.device("cuda")
            elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                self.device = torch.device("mps")
            else:
                self.device = torch.device("cpu")
        else:
            self.device = torch.device(device)
        
        logger.info(f"사용 디바이스: {self.device}")
        
        # 어휘 사전 로딩
        self.vocab = self._load_vocabulary()
        
        # 모델 로딩
        if self.model_type == "pytorch":
            self.model = self._load_pytorch_model()
            self.session = None
        elif self.model_type == "onnx":
            self.model = None
            self.session = self._load_onnx_model()
        else:
            raise ValueError(f"지원하지 않는 모델 타입: {model_type}")
        
        # 모델 정보 로딩
        self.model_info = self._load_model_info()
        
        logger.info(f"모델 로딩 완료: {self.model_type.upper()}")
        logger.info(f"클래스 수: {len(self.vocab)}")
        logger.info(f"특징 크기: {self.model_info.get('data_info', {}).get('feature_size', 274)}")
        logger.info(f"최대 시퀀스 길이: {self.model_info.get('data_info', {}).get('max_sequence_length', 200)}")
    
    def _load_vocabulary(self) -> List[str]:
        """어휘 사전 로딩"""
        vocab = []
        encodings = ['utf-8', 'euc-kr', 'cp949', 'utf-16']
        
        for encoding in encodings:
            try:
                with open(self.vocab_path, "r", encoding=encoding) as f:
                    vocab = [line.strip() for line in f if line.strip()]
                logger.info(f"어휘 사전 로딩 완료 ({encoding}): {len(vocab)}개 클래스")
                break
            except UnicodeDecodeError:
                continue
        
        if not vocab:
            raise VocabularyError(
                f"어휘 사전을 읽을 수 없습니다: {self.vocab_path}",
                vocab_path=self.vocab_path
            )
        
        return vocab
    
    def _load_pytorch_model(self):
        """PyTorch 모델 로딩"""
        try:
            logger.info("PyTorch 모델 로딩 중...")
            
            # 체크포인트 로딩
            checkpoint = torch.load(self.model_path, map_location='cpu', weights_only=False)
            logger.debug(f"체크포인트 타입: {type(checkpoint)}")
            
            # 체크포인트 구조 확인
            if isinstance(checkpoint, dict):
                logger.debug(f"체크포인트 키: {list(checkpoint.keys())}")
                
                # 1. 완전한 모델 객체가 있는 경우
                if 'model' in checkpoint:
                    logger.info("체크포인트에서 'model' 키로 모델 객체 발견")
                    model = checkpoint['model']
                
                # 2. state_dict만 있는 경우 - signjoey 학습 체크포인트
                elif 'model_state_dict' in checkpoint and 'cfg' in checkpoint:
                    logger.info("학습 체크포인트 감지 - SignJoey 모델 재구성")
                    model = self._build_signjoey_model_from_checkpoint(checkpoint)
                
                # 3. 딕셔너리의 첫 번째 값이 모델 객체인지 확인
                else:
                    first_key = list(checkpoint.keys())[0]
                    first_value = checkpoint[first_key]
                    if hasattr(first_value, 'eval'):
                        logger.info(f"체크포인트에서 모델 객체 발견 (키: {first_key})")
                        model = first_value
                    else:
                        raise RuntimeError(
                            f"지원되지 않는 체크포인트 형식입니다. "
                            f"발견된 키: {list(checkpoint.keys())}"
                        )
            else:
                # 모델 객체가 직접 저장된 경우
                logger.info("체크포인트가 모델 객체로 직접 저장됨")
                model = checkpoint
            
            # 모델 객체 검증
            if not hasattr(model, 'eval'):
                raise RuntimeError("로드된 객체가 PyTorch 모델이 아닙니다.")
            
            # 모델을 디바이스로 이동 및 eval 모드 설정
            model = model.to(self.device)
            model.eval()
            
            logger.info("모델 로딩 및 eval 모드 설정 완료")
            return model
            
        except Exception as e:
            if isinstance(e, ModelLoadingError):
                raise
            logger.error(f"PyTorch 모델 로딩 실패: {e}")
            raise ModelLoadingError(
                f"PyTorch 모델 로딩 실패: {e}",
                model_path=self.model_path
            )
    
    def _build_signjoey_model_from_checkpoint(self, checkpoint):
        """SignJoey 학습 체크포인트로부터 모델 재구성"""
        try:
            import sys
            import os
            sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
            
            from signjoey.model import build_model
            
            # 체크포인트에서 설정 정보 추출
            cfg = checkpoint.get('cfg', {})
            
            # 어휘 사전 로드
            trg_vocab = checkpoint.get('trg_vocab')
            if trg_vocab is None:
                raise ValueError("체크포인트에서 어휘 사전을 찾을 수 없습니다.")
            
            logger.info("SignJoey 모델 아키텍처 재구성 중...")
            
            # SignJoey의 build_model 함수 사용
            model = build_model(
                cfg=cfg,
                trg_vocab=trg_vocab
            )
            
            # state_dict 로드
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
                logger.info("모델 가중치를 성공적으로 로드했습니다.")
            else:
                logger.warning("model_state_dict를 찾을 수 없습니다.")
            
            return model
            
        except ImportError as e:
            logger.error(f"SignJoey 모듈을 불러올 수 없습니다: {e}")
            raise ModelLoadingError(
                f"SignJoey 모델 재구성 실패: {e}",
                model_path=self.model_path
            )
        except Exception as e:
            logger.error(f"모델 재구성 중 오류: {e}")
            raise ModelLoadingError(
                f"모델 재구성 실패: {e}",
                model_path=self.model_path
            )
    
    def _load_onnx_model(self):
        """ONNX 모델 로딩"""
        try:
            import onnxruntime as ort
            
            # 프로바이더 설정
            providers = []
            if self.device.type == "cuda":
                providers.append("CUDAExecutionProvider")
            providers.append("CPUExecutionProvider")
            
            session = ort.InferenceSession(self.model_path, providers=providers)
            return session
        except ImportError:
            raise ModelLoadingError(
                "ONNX 런타임이 설치되지 않았습니다. pip install onnxruntime",
                model_path=self.model_path
            )
        except Exception as e:
            raise ModelLoadingError(
                f"ONNX 모델 로딩 실패: {e}",
                model_path=self.model_path
            )
    
    def _load_model_info(self) -> Dict[str, Any]:
        """모델 정보 로딩"""
        info_path = os.path.join(os.path.dirname(self.model_path), "deployment_info.yaml")
        
        if os.path.exists(info_path):
            with open(info_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            # 기본값 반환
            return {
                "data_info": {
                    "feature_size": 274,
                    "max_sequence_length": 128 if self.model_type == "onnx" else 200,
                    "num_classes": len(self.vocab)
                }
            }
    
    def token_from_index_if_valid(self, label_id: int) -> Optional[str]:
        """인덱스로부터 토큰 반환"""
        if 0 <= label_id < len(self.vocab):
            return self.vocab[label_id]
        return None
    
    def predict(
        self,
        keypoints: np.ndarray,
        return_probabilities: bool = False,
        top_k: int = 1
    ) -> Union[str, Dict[str, Any]]:
        """
        키포인트 데이터로부터 수어 예측 수행
        
        Args:
            keypoints: 키포인트 데이터 (seq_len, 274) 또는 (batch_size, seq_len, 274)
            return_probabilities: 확률 분포 반환 여부
            top_k: 상위 k개 예측 반환
            
        Returns:
            예측 결과 (문자열 또는 딕셔너리)
        """
        # 입력 데이터 전처리
        if keypoints.ndim == 2:
            keypoints = keypoints[np.newaxis, :, :]  # (1, seq_len, 274)
        
        # 모델 타입에 따른 추론
        if self.model_type == "pytorch":
            logits = self._predict_pytorch(keypoints)
        else:  # onnx
            logits = self._predict_onnx(keypoints)
        
        # 확률 분포 계산
        probs = torch.softmax(logits, dim=1)

        # 클래스별 가중치 적용 제거 - 순수 모델 성능 확인용
        # class_weights = torch.ones(len(self.vocab), device=probs.device)
        # class_weights[2] = 0.3  # 대구(인덱스 2)의 가중치를 0.3배로 줄임
        # probs = probs * class_weights
        # probs = probs / probs.sum(dim=1, keepdim=True)  # 정규화

        # 상위 k개 예측 추출
        top_probs, top_indices = torch.topk(probs, min(top_k, len(self.vocab)), dim=1)
        
        if return_probabilities:
            result = {
                "top_prediction": self.vocab[top_indices[0, 0].item()],
                "top_confidence": top_probs[0, 0].item() * 100,
                "top_k_predictions": [
                    {
                        "word": self.vocab[top_indices[0, i].item()],
                        "confidence": top_probs[0, i].item() * 100
                    }
                    for i in range(min(top_k, len(self.vocab)))
                ],
                "probabilities": probs[0].detach().cpu().numpy().tolist()
            }
            return result
        else:
            return self.vocab[top_indices[0, 0].item()]
    
    def _predict_pytorch(self, keypoints: np.ndarray) -> torch.Tensor:
        """PyTorch 모델 추론"""
        import torch
        
        # 입력 데이터를 텐서로 변환
        input_tensor = torch.from_numpy(keypoints.astype(np.float32)).to(self.device)
        
        # SignJoey 모델은 src_mask와 src_length를 요구함
        batch_size = input_tensor.size(0)
        seq_len = input_tensor.size(1)
        
        # 마스크 생성 (모든 프레임이 유효하다고 가정)
        src_mask = torch.ones((batch_size, 1, seq_len), dtype=torch.bool, device=self.device)
        
        # 길이 텐서 생성
        src_length = torch.tensor([seq_len] * batch_size, dtype=torch.long, device=self.device)
        
        with torch.no_grad():
            # SignJoey 모델 forward 호출
            loss, logits = self.model(
                src=input_tensor,
                src_mask=src_mask,
                src_length=src_length,
                trg_labels=None  # 추론 시에는 레이블 불필요
            )
        
        return logits
    
    def _predict_onnx(self, keypoints: np.ndarray) -> torch.Tensor:
        """ONNX 모델 추론"""
        # ONNX 모델은 고정 길이 입력을 요구할 수 있음
        seq_len = keypoints.shape[1]
        max_len = self.model_info['data_info']['max_sequence_length']
        
        if seq_len > max_len:
            # 다운샘플링
            indices = np.linspace(0, seq_len - 1, max_len, dtype=int)
            keypoints = keypoints[:, indices, :]
        elif seq_len < max_len:
            # 패딩
            padding = np.zeros((keypoints.shape[0], max_len - seq_len, keypoints.shape[2]))
            keypoints = np.concatenate([keypoints, padding], axis=1)
        
        outputs = self.session.run(None, {"input": keypoints.astype(np.float32)})
        logits = torch.from_numpy(outputs[0])
        
        return logits
    
    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        return {
            "model_type": self.model_type,
            "device": str(self.device),
            "vocabulary": self.vocab,
            "num_classes": len(self.vocab),
            "feature_size": self.model_info['data_info']['feature_size'],
            "max_sequence_length": self.model_info['data_info']['max_sequence_length'],
            "model_path": self.model_path
        }
