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

`app.py`는 웹 서버가 아니라 PC 카메라를 직접 여는 독립 실행형 실시간 인식 프로그램입니다.

## 인식 클래스

기본 Attention 모델은 12개 클래스를 가집니다.

```text
경주, 광명, 대구, 대전, 서울역, 수원,
아산, 영등포, 울산, 천안, 포항, <unk>
```

모델의 검증 지표와 구조는 [deployment README](deployment/README.md)와 각 모델 폴더의 `deployment_info.yaml`에서 확인할 수 있습니다.

## 요구 사항

- Python 3.10 권장
- 서비스 모드만 실행할 때는 카메라가 필요하지 않습니다.
- 로컬 카메라 모드와 카메라 테스트에는 카메라 접근 권한이 필요합니다.
- CUDA가 없어도 ONNX Runtime CPU provider로 실행할 수 있습니다.

## 설치

모델과 설정 경로가 상대 경로이므로 아래 명령은 `server` 디렉터리에서 실행합니다.

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

## Flask 추론 서버 실행

```bash
python ai_server.py
```

정상적으로 모델을 읽으면 `0.0.0.0:5001`에서 서버가 시작됩니다. 현재 별도 health endpoint는 없습니다.

### HTTP 요청

```http
POST /predict_keypoints
Content-Type: application/json
```

요청은 `keypointData` 아래에 한 프레임의 키포인트를 전달합니다.

```json
{
  "recognitionTarget": "DEPARTURE",
  "keypointData": {
    "keypoints": [[0.0, 0.0]]
  }
}
```

`keypointData`에는 다음 두 형식을 사용할 수 있습니다.

- `{ "keypoints": [...] }`
- `{ "body": [...], "face": [...], "leftHand": [...], "rightHand": [...] }`

HTTP 요청은 한 프레임을 전처리한 뒤 마지막 프레임을 복제해 모델 입력 길이를 채웁니다. 동작 시퀀스 전체를 사용하는 방식이 아니므로 실시간 WebSocket 추론과 결과 특성이 다를 수 있습니다.

성공 응답:

```json
{
  "departureCity": "서울역",
  "arrivalCity": null,
  "recognizedProb": 98.7
}
```

`recognizedProb`은 0~1이 아니라 백분율 0~100 범위입니다. 현재 `recognitionTarget` 값과 관계없이 예측 단어는 `departureCity`에 들어갑니다.

### WebSocket 요청

연결 주소:

```text
ws://localhost:5001/ws/predict
```

세션 시작:

```json
{
  "type": "START_SESSION",
  "sessionId": "session-id",
  "recognitionTarget": "DEPARTURE"
}
```

서버는 버퍼를 초기화하고 다음 메시지를 반환합니다.

```json
{"status": "connected"}
```

키포인트 프레임:

```json
{
  "type": "KEYPOINT_FRAME",
  "sessionId": "session-id",
  "frameIndex": 0,
  "timestamp": 0,
  "recognitionTarget": "DEPARTURE",
  "keypoints": [[0.0, 0.0]]
}
```

버퍼가 128프레임에 도달하면 5프레임 간격으로 추론합니다.

## 키포인트 전처리

프레임당 키포인트 순서는 다음과 같습니다.

| 영역 | 인덱스 | 개수 |
| --- | --- | --- |
| Pose | 0~24 | 25 |
| Face | 25~94 | 70 |
| Left hand | 95~115 | 21 |
| Right hand | 116~136 | 21 |

입력 `[137, 2]`는 다음 과정을 거쳐 274차원 특징 벡터가 됩니다.

1. confidence가 없는 점에 세 번째 좌표를 추가합니다.
2. 신체 부위별 정규화를 적용합니다.
3. 코 좌표를 기준으로 Pose 상대 좌표를 계산합니다.
4. NaN과 무한값을 0으로 바꿉니다.
5. x, y 좌표를 평탄화합니다.

## 로컬 카메라 모드

```bash
python app.py
```

`config/realtime_config.yaml`을 읽어 카메라, 모델, 세그멘터, 로깅 옵션을 구성합니다. `q` 키로 종료합니다.

주요 설정:

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

Docker 이미지는 Python 3.10 slim을 사용하고 `ai_server.py`를 실행합니다. 현재 requirements는 CPU용 `onnxruntime`을 설치하므로 CUDA provider를 사용하려면 별도 이미지 구성이 필요합니다.

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
├── realtime/                 # 로컬 실시간 추론과 세그멘터
├── signjoey/                 # 모델 학습·평가 코드
├── tests/                    # 샘플·카메라 추론 테스트
└── utils/                    # 설정, 로깅, 성능, 예외 처리
```

`signjoey`에는 학습·평가 CLI가 남아 있지만 이 저장소에는 바로 사용할 학습 데이터와 완성된 학습 설정 파일이 포함되어 있지 않습니다. 별도 데이터셋과 설정 없이는 학습 명령을 실행할 수 없습니다.

## 테스트

테스트 도구 사용법은 [tests/INFERENCE_TEST_README.md](tests/INFERENCE_TEST_README.md)를 참고합니다.

```bash
python -m tests.test_realtime_inference --sample-only
python -m tests.test_realtime_inference --realtime-only
```

기본 `config/test_config.yaml`은 현재 저장소에 없는 과거 모델 경로를 가리키므로 실행 전에 문서에 적힌 현재 모델 경로로 수정해야 합니다.

## 현재 제한 사항

- WebSocket 추론 응답에 요청의 `sessionId`가 포함되지 않습니다. Spring 백엔드 중계를 사용하려면 응답에 세션 ID를 다시 넣어야 합니다.
- `recognitionTarget`을 수신하지만 결과 필드를 출발역·도착역으로 분기하지 않습니다.
- 서비스가 ONNX 모델 로드에 실패하면 정상 요청을 처리할 수 없습니다.
- HTTP 추론은 단일 프레임 반복 padding을 사용하므로 동작 기반 수어 분류 정확도를 대표하지 않습니다.
- WebSocket 연결별 버퍼는 관리하지만 인증, 메시지 크기 제한, rate limiting은 없습니다.
- `ai_server_faster.py`와 `ai_server_add_log.py`는 별도 실험 파일이며 기본 Docker 실행 대상이 아닙니다.
