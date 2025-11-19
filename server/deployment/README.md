# 배포된 모델 정보

## 📦 모델 파일

이 디렉토리에는 배포용으로 export된 수어 인식 모델이 포함되어 있습니다.

### 파일 목록

- **`multi_class_auto_model.pt`** (3.8 MB) - 배포용 PyTorch 모델
- **`multi_class_auto.onnx`** (약 3.9 MB) - ONNX 런타임 호환 모델
- **`deployment_info.yaml`** - 모델 메타정보 및 설정 (PyTorch/ONNX 공통)
- **`vocabulary.txt`** - 클래스 어휘 사전 (6개 클래스)

## 🎯 모델 정보

- **클래스 수**: 6개
- **클래스 목록**: 급하다, 슬프다, 싫어하다, 안타깝다, 어색하다, <unk>
- **파라미터 수**: 997,486개
- **검증 정확도**: 86.67% (Iteration 270)
- **F1 Score**: 86.48%
- **Best Loss**: 0.338 (낮을수록 좋음)
- **특징 크기**: 274 (137 keypoints × 2)
- **최대 시퀀스 길이**: 200 프레임

## 🏗️ 모델 아키텍처

```
Encoder: GRU (bidirectional)
├─ Hidden Size: 220
├─ Num Layers: 1
└─ Dropout: 0.3

Embeddings: Spatial Embeddings
└─ Embedding Dim: 440

Output Layer: Linear
└─ 6 classes
```

## 🚀 사용 방법

### 1. Python에서 직접 사용 (PyTorch)

```python
from inference_service import SignLanguageInferenceService
import numpy as np

# 서비스 초기화
service = SignLanguageInferenceService(
    model_path="deployment/multi_class_auto_model.pt",
    device="cuda"  # 또는 "cpu"
)

# 키포인트 데이터 준비 (예: 128 프레임, 274 특징)
keypoints = np.load("your_keypoints.npy")  # Shape: (seq_len, 274)

# 예측 수행
result = service.predict(
    keypoints,
    return_probabilities=True,
    top_k=3
)

print(f"예측 결과: {result['top_prediction']}")
print(f"신뢰도: {result['top_confidence']:.2f}%")
```

### 2. REST API 서버 사용 (PyTorch)

### 3. ONNX Runtime으로 추론

```python
import numpy as np
import onnxruntime as ort

session = ort.InferenceSession("deployment/multi_class_auto/multi_class_auto.onnx")

keypoints = np.load("your_keypoints.npy")  # Shape: (seq_len, 274)

if keypoints.ndim == 2:
    keypoints = keypoints[np.newaxis, :, :]

outputs = session.run(None, {"input": keypoints.astype(np.float32)})
logits = outputs[0]
prediction = np.argmax(logits, axis=1)
```

```bash
# 서버 시작
python api_server.py --model_path deployment/multi_class_auto_model.pt --device cuda

# API 호출 (Python)
import requests
import numpy as np

keypoints = np.random.randn(128, 274).tolist()

response = requests.post(
    "http://localhost:5000/predict",
    json={
        "keypoints": keypoints,
        "return_probabilities": True,
        "top_k": 3
    }
)

result = response.json()
print(result['data']['top_prediction'])
```

## 📝 API 엔드포인트

- `GET /health` - 서버 상태 확인
- `GET /model/info` - 모델 정보 조회
- `POST /predict` - 단일 예측
- `POST /predict/batch` - 배치 예측
- `POST /predict/file` - CSV 파일로부터 예측

## 📊 입력 형식

### 키포인트 데이터

```python
# 형식 1: (seq_len, 274)
keypoints = np.array([
    [x1_pose, y1_pose, x2_pose, y2_pose, ..., x1_hand, y1_hand, ...],  # Frame 1
    [x1_pose, y1_pose, x2_pose, y2_pose, ..., x1_hand, y1_hand, ...],  # Frame 2
    ...
])

# 형식 2: (seq_len, 137, 2)
keypoints = np.array([
    [[x1, y1], [x2, y2], ..., [x137, y137]],  # Frame 1
    [[x1, y1], [x2, y2], ..., [x137, y137]],  # Frame 2
    ...
])
```

### 키포인트 구성

- **Pose**: 25 keypoints (0-24)
- **Face**: 70 keypoints (25-94)
- **Hands**: 42 keypoints (95-136)
  - Left Hand: 21 keypoints (95-115)
  - Right Hand: 21 keypoints (116-136)

**총 137 keypoints × 2 (x, y) = 274 features**

## 🔧 요구사항

```bash
pip install torch numpy pyyaml
# API 서버용
pip install flask flask-cors pandas
```

## 📚 추가 문서

- `DEPLOYMENT_GUIDE.md` - 상세한 배포 가이드
- `README.md` (프로젝트 루트) - 전체 프로젝트 문서

## ⚠️ 주의사항

1. **PyTorch 버전**: PyTorch 2.6+ 호환성 확인됨
2. **입력 정규화**: 키포인트는 이미 정규화된 상태여야 합니다
3. **시퀀스 길이**: 가변 길이 지원 (최대 200 프레임 권장)
4. **디바이스**: GPU 사용 시 CUDA가 설치되어 있어야 합니다
5. **ONNX 추론**: `onnxruntime` 1.16+ 권장, 입력은 `float32` 형식 유지

## 📞 문의

문제가 발생하면 프로젝트 이슈 트래커에 보고해주세요.
