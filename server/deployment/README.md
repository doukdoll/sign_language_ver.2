# 배포 모델

서비스에서 사용할 ONNX 모델, 어휘 파일, 학습·검증 메타데이터를 보관합니다.

## 모델 목록

| 폴더 | Encoder | 입력 크기 | 검증 Accuracy | F1 weighted | 용도 |
| --- | --- | --- | ---: | ---: | --- |
| `20251109-1439_Attention` | Masked Attention | 180 × 274 | 0.9879 | 0.9876 | 현재 기본 모델 |
| `20251109-1439_GRU` | Bidirectional GRU | 180 × 274 | 0.2909 | 0.1995 | 비교용 모델 |

`ai_server.py`와 `config/realtime_config.yaml`은 기본적으로 Attention 모델을 사용합니다.

## 파일 구성

```text
deployment/
├── inference_service.py
├── 20251109-1439_Attention/
│   ├── 20251109-1439.onnx
│   ├── vocabulary.txt
│   └── deployment_info.yaml
├── 20251109-1439_GRU/
│   ├── 20251109-1439.onnx
│   ├── vocabulary.txt
│   └── deployment_info.yaml
└── README.md
```

- `.onnx`: ONNX Runtime용 추론 모델
- `vocabulary.txt`: 출력 인덱스 순서와 동일한 클래스 목록
- `deployment_info.yaml`: 모델 구조, 입력 크기, 학습 결과, export 정보
- `inference_service.py`: PyTorch와 ONNX 모델을 공통 인터페이스로 감싸는 클래스

## 입력 형식

모델은 `float32` 배열을 입력받습니다.

```text
(sequence_length, 274)
또는
(batch_size, sequence_length, 274)
```

274개 feature는 137개 키포인트의 x, y 좌표입니다.

| 영역 | 키포인트 수 | feature 수 |
| --- | ---: | ---: |
| Pose | 25 | 50 |
| Face | 70 | 140 |
| Left hand | 21 | 42 |
| Right hand | 21 | 42 |
| 합계 | 137 | 274 |

ONNX 모델 메타데이터의 최대 시퀀스 길이는 180입니다. `SignLanguageInferenceService`는 긴 입력을 균등 다운샘플링하고 짧은 입력의 뒤쪽을 0으로 padding합니다.

## 출력 클래스

다음은 기본 Attention 모델의 실제 `vocabulary.txt` 순서입니다.

```text
경주
광명
대구
대전
서울
수원
아산
영등포
울산
천안
포항
<unk>
```

GRU 모델의 같은 인덱스(0-based 4)는 `서울역`입니다. Attention의 `deployment_info.yaml`에도 `서울역`이 남아 있지만, 런타임 응답은 메타데이터가 아닌 각 모델의 `vocabulary.txt`를 사용합니다. 두 모델의 결과를 비교할 때 이 표기 차이를 구분해야 합니다.

## Python에서 추론

아래 코드는 `server` 디렉터리에서 실행하는 것을 기준으로 합니다.

```python
import numpy as np

from deployment.inference_service import SignLanguageInferenceService

service = SignLanguageInferenceService(
    model_path="deployment/20251109-1439_Attention/20251109-1439.onnx",
    vocab_path="deployment/20251109-1439_Attention/vocabulary.txt",
    model_type="onnx",
    device="auto",
)

keypoints = np.zeros((180, 274), dtype=np.float32)
result = service.predict(
    keypoints,
    return_probabilities=True,
    top_k=3,
)

print(result["top_prediction"])
print(result["top_confidence"])
print(result["top_k_predictions"])
```

반환값의 `top_confidence`와 `top_k_predictions[*].confidence`는 0~100 백분율입니다.

## ONNX Runtime 직접 호출

```python
import numpy as np
import onnxruntime as ort

session = ort.InferenceSession(
    "deployment/20251109-1439_Attention/20251109-1439.onnx",
    providers=["CPUExecutionProvider"],
)

keypoints = np.zeros((1, 180, 274), dtype=np.float32)
logits = session.run(None, {"input": keypoints})[0]
prediction_index = int(np.argmax(logits, axis=1)[0])
```

ONNX 출력은 logits이므로 확률이 필요하면 softmax를 별도로 적용해야 합니다.

## Attention 모델 상세

```text
Encoder: masked_attention
Embedding: spatial, 512 dimensions
Hidden size: 256
Layers: 1
Bidirectional: true
Classes: 12
Sequence length: 180
Feature size: 274
ONNX opset: 12
```

`deployment_info.yaml`에 기록된 검증 결과:

- Accuracy: 0.9878787879
- F1 macro: 0.9876413909
- F1 weighted: 0.9876413909
- WER: 0.0121212121

이 수치는 해당 학습·검증 데이터 분할에서 얻은 값이며 실제 키오스크 환경의 일반화 성능을 보장하지 않습니다.

## GRU 모델 상세

```text
Encoder: gru
Embedding: spatial, 384 dimensions
Hidden size: 192
Layers: 1
Bidirectional: true
Classes: 12
Sequence length: 180
Feature size: 274
ONNX opset: 12
```

## 주의 사항

- 모델 입력 전에 학습 때와 동일한 키포인트 순서와 정규화를 적용해야 합니다.
- `vocabulary.txt`의 줄 순서를 변경하면 출력 클래스가 잘못 매핑됩니다.
- 기본 requirements는 CPU용 `onnxruntime`입니다. CUDA 실행에는 호환되는 `onnxruntime-gpu` 환경이 필요합니다.
- 모델 파일명은 두 폴더에서 동일하므로 경로를 폴더까지 정확히 지정해야 합니다.
- 과거 문서에 언급된 `multi_class_auto`, `20251014-202250`, REST `/predict` 서버 파일은 현재 저장소에 없습니다.
