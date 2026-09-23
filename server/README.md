# AI Server

MediaPipe/OpenPose 순서의 키포인트를 전처리하고 ONNX 모델로 기차역 수어를 분류하는 Python 모듈입니다. Flask HTTP·WebSocket 서비스와 로컬 카메라 실행 모드를 함께 포함합니다.

## 현재 서비스 구성

기본 서버 진입점은 `ai_server.py`입니다.

- HTTP: `POST /predict_keypoints`
- WebSocket: `/ws/predict`
- Port: `5001`
- 기본 모델: `deployment/20251109-1439_Attention/20251109-1439.onnx`
- 기본 어휘: `deployment/20251109-1439_Attention/vocabulary.txt`
- 모델 입력: 180 frames × 274 features
- 서버 WebSocket 버퍼: 128 frames, 5 frames마다 추론 시도

HTTP 경계는 `realtime/http_api.py`의 Flask 앱 factory에서 검증하고, `ai_server.py`가 실제 전처리·모델 함수를 연결합니다. HTTP와 WebSocket은 같은 추론 잠금으로 모델 호출을 직렬화하며, WebSocket 버퍼는 연결·세션별로 분리합니다.

`app.py`는 웹 서버가 아니라 PC 카메라를 직접 여는 독립 실행형 실시간 인식 프로그램입니다.

## 인식 클래스

기본 Attention 모델은 12개 클래스를 가집니다.

```text
경주, 광명, 대구, 대전, 서울, 수원,
아산, 영등포, 울산, 천안, 포항, <unk>
```

위 목록은 실제 Attention `vocabulary.txt` 기준입니다. 메타데이터와 GRU 어휘에는 `서울역`으로 기록되어 있어 표기가 다릅니다. 모델의 기존 검증 지표와 구조는 [deployment README](deployment/README.md)와 각 모델 폴더의 `deployment_info.yaml`에서 확인할 수 있습니다.

## 요구 사항

- Python 3.10 권장
- 서비스 모드만 실행할 때는 카메라가 필요하지 않습니다.
- 로컬 카메라 모드와 카메라 테스트에는 카메라 접근 권한이 필요합니다.
- CUDA가 없어도 ONNX Runtime CPU provider로 실행할 수 있습니다.
- `requirements.txt`는 headless OpenCV를 포함하므로 `app.py`의 OpenCV 창을 사용하려면 별도의 GUI 지원 환경이 필요합니다. 서비스 전용 CPU 설치는 [실행 기록](../docs/LIVE_RECOGNITION_CHECK.md)을 참고합니다.

## 설치

모델과 설정 경로가 상대 경로이므로 아래 명령은 `server` 디렉터리에서 실행합니다.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install "torch==2.14.0+cpu" --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-smoke.txt
python -m pip check
```

위 조합은 Windows/Python 3.10에서 실제 CPU ONNX 연결 스모크에 사용한 서비스 전용 환경입니다. MediaPipe 카메라·학습·오프라인 전처리 패키지는 포함하지 않습니다. OS별 CPU PyTorch wheel 지원 여부는 별도로 확인해야 하며 다른 플랫폼에서 같은 설치를 검증한 것은 아닙니다.

기존 전체 의존성이 필요한 개발 환경에서는 별도 가상환경에 다음 파일을 사용할 수 있습니다. 전체 패키지 조합의 새 설치·학습 실행은 최근 CI와 서비스 스모크의 검증 범위가 아닙니다.

```bash
python -m pip install -r requirements.txt
```

macOS/Linux 가상환경 활성화 명령은 `source .venv/bin/activate`입니다.

## Flask 추론 서버 실행

```bash
python ai_server.py
```

`0.0.0.0:5001`에서 서버가 시작됩니다. 모델을 읽지 못한 상태에서는 HTTP 추론에 503, WebSocket START에 `MODEL_NOT_READY`를 반환합니다. 현재 별도 health endpoint는 없습니다.

### HTTP 요청

```http
POST /predict_keypoints
Content-Type: application/json
```

요청은 `keypointData` 아래에 한 프레임의 키포인트 137개를 전달합니다. 다음 코드는 요청 구조를 생성하는 예시이며, 모든 점이 동일한 합성 입력은 정확도 검증용이 아닙니다.

```python
payload = {
    "recognitionTarget": "DEPARTURE",
    "keypointData": {"keypoints": [[0.5, 0.5, 1.0] for _ in range(137)]},
}
```

`keypointData`에는 다음 형식을 사용할 수 있습니다.

- `{ "keypoints": [...] }`
- `{ "body": [...], "face": [...], "leftHand": [...], "rightHand": [...] }` — 각각 25·70·21·21개
- 키포인트 137개의 배열을 직접 전달하는 기존 형식

한 프레임의 각 점은 모두 `[x, y]` 또는 모두 `[x, y, confidence]`여야 합니다. 좌표는 유한한 숫자이며 confidence는 0~1입니다. 3열 형식의 결측점은 `[null, null, 0]`입니다. 잘못된 개수·혼합 열 수·문자열·불리언·NaN/Infinity는 전처리 전에 거부합니다.

HTTP 요청은 한 프레임을 전처리한 뒤 같은 프레임을 128개로 복제하고, ONNX 서비스에서 나머지 52프레임을 0으로 채웁니다. 동작 시퀀스 전체를 사용하는 방식이 아니므로 실시간 WebSocket 추론과 결과 특성이 다를 수 있습니다.

성공 응답:

```json
{
  "departureCity": "서울",
  "arrivalCity": null,
  "recognizedProb": 98.7
}
```

`recognizedProb`은 0~1이 아니라 백분율 0~100 범위입니다. `recognitionTarget`이 `DEPARTURE`이면 `departureCity`, `ARRIVAL`이면 `arrivalCity`에 예측 단어를 넣고 반대 필드는 `null`입니다. target을 생략하면 기존 클라이언트 호환을 위해 `DEPARTURE`로 처리합니다. 명시적인 다른 값이나 `null`은 400입니다.

실패를 `200`의 `인식 중...`으로 숨기지 않으며, 오류 응답은 다음 필드를 사용합니다. 내부 예외 내용은 서버 로그에만 남깁니다.

```json
{
  "errorCode": "MODEL_NOT_READY",
  "errorMessage": "model is not ready"
}
```

- 400: `INVALID_REQUEST` 또는 `INVALID_KEYPOINTS` — JSON·대상·키포인트 입력 오류
- 503: `MODEL_NOT_READY` — 모델 초기화 실패
- 500: `INFERENCE_FAILED` — 추론 예외 또는 유효하지 않은 모델 결과

### WebSocket 요청

[WebSocket 규약 v1](../docs/RECOGNITION_PROTOCOL.md)을 사용합니다. 연결 주소는 ws://localhost:5001/ws/predict입니다.

- START/RESET/END에 명시적인 확인 응답을 반환합니다.
- 하나의 BE 연결에서도 sessionId별 버퍼·revision·frameIndex·인식 대상을 분리합니다.
- 모든 세션 응답에는 ID·revision이 포함되며, DEPARTURE/ARRIVAL에 따라 도시 필드가 달라집니다.
- 프레임 입력은 137 × 3 [x, y, confidence]입니다. 결측점은 [null, null, 0]을 사용합니다.
- 유휴 만료는 realtime.session_idle_timeout(기본 120초)로 설정합니다.
- 기존 128프레임 버퍼와 5프레임 추론 간격, 모델 내부 180프레임 padding 정책은 유지합니다.

모델 없이 실행하는 세션 회귀 테스트: `python -S -m unittest tests.test_sessions -v`

실제 CPU ONNX 연결 검증 환경과 최소 의존성 설치 방법은 [실행 기록](../docs/LIVE_RECOGNITION_CHECK.md)을 참고합니다.

## 키포인트 전처리

프레임당 키포인트 순서는 다음과 같습니다.

| 영역 | 인덱스 | 개수 |
| --- | --- | --- |
| Pose | 0~24 | 25 |
| Face | 25~94 | 70 |
| Left hand | 95~115 | 21 |
| Right hand | 116~136 | 21 |

WebSocket 입력은 `[137, 3]`이며 다음 과정을 거쳐 274차원 특징 벡터가 됩니다. HTTP의 기존 `[137, 2]` 입력은 confidence를 0으로 보충하므로 confidence가 있는 입력과 전처리 결과가 다를 수 있습니다.

1. `[x, y, confidence]`를 읽습니다. HTTP에서 confidence가 없으면 0을 추가합니다.
2. 신체 부위별 정규화를 적용합니다.
3. 코 좌표를 기준으로 Pose 상대 좌표를 계산합니다.
4. NaN과 무한값을 0으로 바꿉니다.
5. x, y 좌표를 평탄화합니다.

## 로컬 카메라 모드

```bash
python app.py
```

`config/realtime_config.yaml`을 읽어 카메라, 모델, 세그멘터, 로깅 옵션을 구성합니다. `q` 키로 종료합니다.

웹 서비스에서 호출되지 않던 `AdvancedHandValidator` 초기화는 제거했습니다. 로컬 카메라 모드의 품질 검증기·세그멘터와 기존 학습·실험 코드는 그대로 유지합니다.

주요 설정:

아래는 YAML에 저장된 값입니다. 현재 `app.py` 경로도 ONNX 모드에서는 `realtime/app_main.py`가 버퍼를 128로 고정하므로 `window_size: 180`을 읽어 180프레임을 수집하는 것은 아닙니다. 모델 입력은 별도 0 padding을 통해 180프레임이 됩니다.

```yaml
model:
  path: "deployment/20251109-1439_Attention/20251109-1439.onnx"
  vocab_path: "deployment/20251109-1439_Attention/vocabulary.txt"
  type: "onnx"
  device: "auto"

realtime:
  window_size: 180
  fps_target: 24.0
```

## Docker

```bash
docker build -t sign-language-ai .
docker run --rm -p 5001:5001 sign-language-ai
```

Docker 이미지는 Python 3.10 slim과 기존 전체 `requirements.txt`를 사용하고 `ai_server.py`를 실행합니다. 이미지 빌드는 현재 CI의 검증 범위가 아닙니다. 현재 requirements는 CPU용 `onnxruntime`을 설치하므로 CUDA provider를 사용하려면 별도 이미지 구성이 필요합니다.

## 프로젝트 구조

```text
server/
├── ai_server.py              # 기본 Flask HTTP/WebSocket 서버
├── ai_server_faster.py       # 실험용 빠른 처리 변형
├── ai_server_add_log.py      # 실험용 상세 로깅 변형
├── app.py                    # 로컬 카메라 진입점
├── config/                   # 실시간·테스트 YAML 설정
├── deployment/               # ONNX 모델, 어휘, 메타데이터
├── input_keypoint/           # 변환, 정규화, 손 필터, 검증
├── realtime/                 # HTTP 앱 factory, WS 세션, 로컬 추론, 세그멘터
├── signjoey/                 # 모델 학습·평가 코드
├── requirements-test.txt      # 모델 없는 HTTP 테스트용 Flask
├── tests/                    # HTTP·세션 회귀 테스트, 수동 추론 도구
└── utils/                    # 설정, 로깅, 성능, 예외 처리
```

`signjoey`에는 학습·평가 CLI가 남아 있지만 이 저장소에는 바로 사용할 학습 데이터와 완성된 학습 설정 파일이 포함되어 있지 않습니다. 별도 데이터셋과 설정 없이는 학습 명령을 실행할 수 없습니다.

## 테스트

`server` 디렉터리에서 실행합니다. Python 3.10 표준 라이브러리만 사용하는 세션 회귀 테스트 15개는 모델·카메라·pip 설치가 필요하지 않습니다.

```bash
python -S -m unittest tests.test_sessions -v
```

HTTP 회귀 테스트 15개는 Flask test client로 실제 요청·응답 경계를 검사합니다. 앱 factory에 테스트용 전처리·예측 함수를 전달하므로 모델·torch·NumPy·ONNX Runtime·카메라 없이 실행할 수 있습니다.

```bash
python -m pip install -r requirements-test.txt
python -m unittest tests.test_http_api -v
```

`requirements-test.txt`는 테스트용 Flask만 설치하며 서비스 실행용 의존성을 대체하지 않습니다. `-S`는 site-packages를 제외하므로 Flask가 필요한 HTTP 테스트에는 사용하지 않습니다.

[GitHub Actions CI](../.github/workflows/ci.yml)는 `develop` 대상 PR과 `develop` push에서 세션·HTTP 테스트를 실행합니다. 현재 변경의 30개 테스트는 로컬에서 통과했으며 원격 결과는 [PR #20](https://github.com/doukdoll/sign_language_ver.2/pull/20)의 최종 커밋 Checks에서 확인합니다. 이전 PR #18의 성공 기록은 당시 세션 15개 기준입니다. CI 범위와 재현 명령은 [CI 가이드](../docs/CI.md)를 참고합니다. 실제 ONNX 추론·카메라·정확도 검증은 CI에 포함되지 않습니다.

아래 수동 테스트 도구는 모델 및 관련 의존성이 필요합니다. 사용법은 [tests/INFERENCE_TEST_README.md](tests/INFERENCE_TEST_README.md)를 참고합니다.

```bash
python -m tests.test_realtime_inference --sample-only
python -m tests.test_realtime_inference --realtime-only
```

기본 `config/test_config.yaml`은 현재 저장소에 없는 과거 모델 경로를 가리키므로 실행 전에 문서에 적힌 현재 모델 경로로 수정해야 합니다.

## 현재 제한 사항

- 서비스가 ONNX 모델 로드에 실패하면 정상 요청을 처리할 수 없습니다.
- HTTP 추론은 단일 프레임 반복 padding을 사용하므로 동작 기반 수어 분류 정확도를 대표하지 않습니다.
- WebSocket 연결·세션별 버퍼는 관리하지만 인증, 메시지 크기 제한, rate limiting은 없습니다.
- `ai_server_faster.py`와 `ai_server_add_log.py`는 별도 실험 파일이며 기본 Docker 실행 대상이 아닙니다.
