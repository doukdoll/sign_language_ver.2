# KSLT 프로젝트 구조 가이드

이 프로젝트는 배포된 모델을 사용한 실시간 한국 수어 인식 시스템입니다.

## 📁 프로젝트 구조

```
KSLT/
├── app.py                                    # 메인 실행 파일
├── requirements.txt                          # 의존성 목록
├── README.md                                # 프로젝트 문서
├── PROJECT_STRUCTURE.md                     # 프로젝트 구조 가이드
│
├── deployment/                              # 배포된 모델 및 서비스
│   ├── inference_service.py                 # 배포 모델 추론 서비스
│   ├── multi_class_auto/                    # PyTorch 배포 모델
│   │   ├── multi_class_auto_model.pt        # PyTorch 모델 (3.8MB)
│   │   ├── vocabulary.txt                   # 어휘 사전 (6개 클래스)
│   │   └── deployment_info.yaml             # 모델 메타정보
│   ├── 20251014-202250/                     # ONNX 배포 모델
│   │   ├── 20251014-202250.onnx             # ONNX 모델 (4.7MB)
│   │   ├── vocabulary.txt                   # 어휘 사전
│   │   └── deployment_info.yaml             # 모델 메타정보
│   └── README.md                            # 배포 모델 사용 가이드
│
├── realtime/                                # 실시간 인식 시스템
│   ├── app_main.py                          # 실시간 수어 인식 메인 로직
│   ├── segmenter.py                         # 온라인 세그멘테이션
│   ├── inference_utils.py                   # 배포 모델 추론 유틸리티
│   ├── inference_logger.py                  # 추론 결과 로깅
│   └── visualization.py                    # 시각화 도구
│
├── input_keypoint/                          # 키포인트 처리
│   ├── mediapipe_to_openpose.py             # MediaPipe → OpenPose 변환
│   ├── integrated_keypoint_processor_optimized.py  # 통합 키포인트 처리
│   ├── bodypart_normalization_processor.py   # 신체 부위 정규화
│   ├── advanced_validators.py               # 고급 검증 도구
│   ├── hand_filtering.py                   # 손 필터링
│   ├── hands.py                            # 손 처리 유틸리티
│   └── check_points.py                     # 키포인트 검증
│
├── data/                                    # 데이터 및 결과
│   └── auto_generated_vocab.docx            # 어휘 사전 문서
│
├── docs/                                    # 문서
│   ├── BODYPART_NORM_QUICKSTART.md          # 신체 부위 정규화 빠른 시작
│   └── BODYPART_NORMALIZATION_GUIDE.md     # 신체 부위 정규화 가이드
│
└── scripts/                                 # 유틸리티 스크립트
    ├── compare_normalization_methods.py     # 정규화 방법 비교
    └── infer_from_csv.py                    # CSV 파일 추론
```

## 🚀 실행 방법

### 실시간 수어 인식

```bash
python app.py
```

### 파일 기반 추론

```python
from realtime.app_main import inference_from_file
inference_from_file()
```

## 🎯 주요 특징

### 배포 모델 지원

- **PyTorch 모델**: `deployment/multi_class_auto/multi_class_auto_model.pt`
- **ONNX 모델**: `deployment/20251014-202250/20251014-202250.onnx`
- **자동 디바이스 선택**: CUDA → MPS → CPU
- **고정 길이 입력**: PyTorch(200프레임), ONNX(128프레임)

### 실시간 처리 파이프라인

1. **MediaPipe 키포인트 추출**: Pose, Face, Hands
2. **OpenPose 형식 변환**: 274차원 특징 벡터
3. **슬라이딩 윈도우**: 실시간 버퍼링
4. **온라인 세그멘테이션**: 속도+확률 기반 방출
5. **동적 임계값 튜닝**: FPS 기반 성능 최적화

### 인식 클래스 (6개)

- 급하다
- 슬프다
- 싫어하다
- 안타깝다
- 어색하다
- <unk>

## 🔧 설정 변경

### 모델 타입 변경

`realtime/app_main.py`에서:

```python
MODEL_TYPE = "pytorch"  # "pytorch" 또는 "onnx"
```

### 윈도우 크기 조정

```python
WIN = 200 if MODEL_TYPE == "pytorch" else 128
```

### 세그멘테이션 파라미터 튜닝

```python
segmenter = OnlineSegmenter(
    prob_thr=0.62,      # 확률 임계값
    fuse_tau=0.65,      # 융합 임계값
    min_on=7,           # 최소 연속 프레임
    cooldown=14,        # 쿨다운 프레임
    w_motion=0.5,       # 속도 가중치
    w_prob=0.5,         # 확률 가중치
)
```

## 📊 성능 최적화

### FPS 기반 동적 조정

- 15프레임마다 FPS 측정
- 성능 저하 시 임계값 자동 완화
- 지수 이동 평균으로 안정화

### 메모리 효율성

- `deque(maxlen=WIN)`으로 고정 크기 버퍼
- 불필요한 텐서 즉시 해제
- 배치 처리 최적화

## 🛠️ 개발 도구

### 로깅

- 추론 결과 CSV 저장
- 키포인트 윈도우 저장 (선택사항)
- 실시간 성능 모니터링

### 시각화

- MediaPipe 랜드마크 오버레이
- 인식 결과 텍스트 표시
- 한국어 폰트 지원

## 📝 API 사용법

### 추론 서비스 직접 사용

```python
from deployment.inference_service import SignLanguageInferenceService

service = SignLanguageInferenceService(
    model_path="deployment/multi_class_auto/multi_class_auto_model.pt",
    vocab_path="deployment/multi_class_auto/vocabulary.txt",
    model_type="pytorch"
)

result = service.predict(keypoints, return_probabilities=True, top_k=3)
print(f"예측: {result['top_prediction']}")
print(f"신뢰도: {result['top_confidence']:.2f}%")
```

## ⚠️ 주의사항

1. **카메라 권한**: 시스템 설정에서 Python 카메라 접근 허용
2. **의존성**: `pip install -r requirements.txt`
3. **모델 파일**: 배포 모델 파일이 올바른 경로에 있는지 확인
4. **GPU 지원**: CUDA 설치 시 자동 GPU 가속
5. **실시간 성능**: 고성능 GPU 권장 (CPU도 지원)

## 🔄 업데이트 히스토리

- **v2.0**: 배포 모델 기반 시스템으로 전환
- **v1.0**: SignJoey 프레임워크 기반 시스템
