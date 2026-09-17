# 추론 테스트

`test_realtime_inference.py`는 배포 모델을 가상 입력 또는 로컬 카메라 입력으로 확인하는 수동 테스트 도구입니다. pytest 테스트가 아니라 직접 실행하는 CLI 프로그램입니다.

## 제공 모드

| 옵션 | 동작 |
| --- | --- |
| `--sample-only` | random, zeros, constant, normal 배열로 모델 추론 |
| `--realtime-only` | 카메라 → MediaPipe → 정규화 → 모델 추론 |
| 옵션 없음 | 샘플 테스트 후 카메라 테스트를 연속 실행 |
| `--config PATH` | 기본 파일 대신 지정한 YAML 사용 |

## 실행 전 모델 경로 수정

현재 `config/test_config.yaml`은 저장소에 없는 과거 경로 `deployment/20251105-2043`을 가리킵니다. 실행 전에 아래처럼 현재 모델로 변경해야 합니다.

```yaml
model:
  path: "deployment/20251109-1439_Attention/20251109-1439.onnx"
  vocab_path: "deployment/20251109-1439_Attention/vocabulary.txt"
  type: "onnx"
  device: "auto"

realtime:
  window_size: 180
```

설정의 상대 경로는 `server` 디렉터리를 기준으로 해석됩니다.

## 실행

모든 명령은 `server` 디렉터리에서 실행합니다.

### 샘플 입력만 테스트

```bash
python -m tests.test_realtime_inference --sample-only
```

카메라 없이 모델 로드와 추론 경로를 확인할 수 있습니다. 샘플 입력은 실제 수어 키포인트가 아니므로 예측 단어와 신뢰도는 모델 품질 평가 자료로 사용할 수 없습니다.

### 카메라만 테스트

```bash
python -m tests.test_realtime_inference --realtime-only
```

프로그램은 설정된 카메라 인덱스 `[0, 1, 2]`를 순서대로 시도합니다. OpenCV 창에서 `q` 키를 누르면 종료됩니다.

### 전체 테스트

```bash
python -m tests.test_realtime_inference
```

샘플 입력 테스트를 먼저 실행한 뒤 카메라 테스트를 시작합니다.

### 다른 설정 파일 사용

```bash
python -m tests.test_realtime_inference --config config/my_test_config.yaml
```

절대 경로도 사용할 수 있습니다.

## 카메라 파이프라인

```text
OpenCV camera
  └─ MediaPipe Holistic
       └─ MediaPipe → OpenPose 순서 변환
            └─ BodyPartNormalizationProcessor
                 └─ 274차원 특징 벡터
                      └─ sliding window
                           └─ SignLanguageInferenceService
```

키포인트 구성:

- Pose: 25개
- Face: 70개
- Left hand: 21개
- Right hand: 21개
- 합계: 137개 × x, y = 274 features

## 주요 설정

`config/test_config.yaml`에서 다음 값을 조정할 수 있습니다.

```yaml
realtime:
  window_size: 180
  fps_target: 30.0

  camera:
    indices: [0, 1, 2]
    width: 640
    height: 480
    fps: 30

  mediapipe:
    min_detection_confidence: 0.5
    min_tracking_confidence: 0.5

  normalization:
    confidence_threshold: 0.3
    bbox_padding: 0.1
    image_width: 640
    image_height: 480

test:
  realtime_test:
    show_landmarks: true
    show_confidence: true
    show_fps: true
    show_frame_count: true
    log_interval: 30
    top_k_predictions: 3
```

`normalization.enable_bodypart_norm` 설정값은 파일에 존재하지만 테스트 코드는 `BodyPartNormalizationProcessor`를 항상 생성하고 사용합니다. 현재 구현에서는 이 값을 `false`로 바꿔도 정규화가 비활성화되지 않습니다.

## 출력

샘플 테스트는 각 입력 유형에 대해 다음 정보를 로그로 남깁니다.

- top prediction
- confidence
- top-k predictions
- 추론 중 발생한 오류

카메라 테스트는 프레임 위에 다음 정보를 표시할 수 있습니다.

- MediaPipe landmarks
- 현재 예측과 confidence
- FPS와 frame count

## 문제 해결

### 모델 파일을 찾을 수 없음

`config/test_config.yaml`의 `model.path`와 `model.vocab_path`를 현재 `deployment` 폴더와 대조합니다.

```text
deployment/20251109-1439_Attention/20251109-1439.onnx
deployment/20251109-1439_Attention/vocabulary.txt
```

### 카메라를 열 수 없음

- Zoom, Teams, 브라우저 등 카메라를 점유한 프로그램을 종료합니다.
- 운영체제의 카메라 권한에서 Python 또는 터미널 접근을 허용합니다.
- YAML의 `camera.indices` 순서를 실제 장치에 맞게 바꿉니다.

### 화면은 뜨지만 추론이 시작되지 않음

- `window_size`만큼 유효 프레임이 버퍼에 쌓여야 합니다.
- 모델 메타데이터의 시퀀스 길이와 `window_size`를 180으로 맞춥니다.
- 손과 얼굴이 카메라 프레임 안에서 안정적으로 감지되는지 확인합니다.

### ONNX Runtime provider 오류

기본 requirements는 CPU provider를 사용합니다. CUDA를 지정하려면 CUDA 버전과 호환되는 `onnxruntime-gpu` 환경을 별도로 구성해야 합니다.

## 한계

- 자동 assertion이나 합격 기준이 없는 수동 진단 도구입니다.
- random/zero 입력 결과는 정확도 검증이 아닙니다.
- 실시간 테스트는 카메라, 조명, CPU/GPU 성능에 영향을 받습니다.
- 현재 기본 YAML의 모델 경로는 수정 전에는 실행되지 않습니다.
