# 수어 기반 기차 예매 키오스크

문서 확인 기준: 2026-09-22, `develop`의 실시간 세션 연동·프론트 정적 검사 정리·CI 구성 반영 상태.

웹캠으로 수어 동작을 입력받아 출발역과 도착역을 인식하고, 열차 조회부터 좌석 선택과 결제 화면까지 이어지는 키오스크형 프로토타입입니다.

이 저장소는 다음 세 애플리케이션으로 구성됩니다.

| 모듈 | 역할 | 기술 |
| --- | --- | --- |
| `frontend` | 키오스크 UI, 카메라 입력, MediaPipe 키포인트 추출 | React 19, TypeScript, Vite 7, Tailwind CSS 4 |
| `backend` | 열차 조회·예매 API, WebSocket 중계, H2 데이터 관리 | Java 17, Spring Boot 3.2.5, JPA, WebSocket |
| `server` | 키포인트 전처리와 ONNX 수어 추론 | Python 3.10, Flask, ONNX Runtime, PyTorch, MediaPipe |

## 현재 구현 상태

이 프로젝트는 완성된 운영 서비스가 아니라 대학 프로젝트 단계의 프로토타입입니다.

| 기능 | 상태 | 실제 동작 |
| --- | --- | --- |
| 출발역·도착역 카메라 입력 | 구현 | 브라우저에서 MediaPipe로 137개 키포인트를 추출합니다. |
| 실시간 역 이름 추론 | 연동 구현 | 세션 소유권·RESET·재접속을 구현하고 실제 ONNX까지 합성 입력 연결 검증을 완료했습니다. 인식 정확도 평가는 별도입니다. |
| 열차 시간표 조회 | 구현 | 백엔드가 CSV에서 적재한 경부선 시간표를 H2에서 조회합니다. 조회 실패 시 프론트는 mock 시간표를 표시합니다. |
| 승객 수·여정 유형·날짜 입력 | 임시 구현 | UI 입력값을 사용하지만 관련 수어 REST API 응답은 현재 고정값입니다. |
| 좌석 선택 | UI 구현 | 프론트 상태로만 관리하며 실제 좌석 재고와 연동되지 않습니다. |
| 예매 생성 | 백엔드 구현 | `POST /api/booking/train`이 예매와 QR 문자열을 생성하지만 현재 프론트 결제 흐름에서는 호출하지 않습니다. |
| 결제 | 시뮬레이션 | 프론트에서 6초 대기와 300ms 페이드 후 완료 화면으로 이동합니다. 백엔드 결제 API는 구현되지 않았습니다. |

## 시스템 흐름

```text
브라우저 카메라
  └─ MediaPipe Holistic
       └─ 137 keypoints (Pose 25 + Face 70 + Hands 42)
            └─ WebSocket: /api/sign/stream
                 └─ Spring Boot 중계
                      └─ WebSocket: /ws/predict
                           └─ Flask + ONNX 추론 서버
```

열차 조회와 예매는 별도의 HTTP API로 처리됩니다.

```text
React ── HTTP ──> Spring Boot ── JPA ──> H2 / MySQL
```

## 디렉터리 구조

```text
sign_language_ver.2/
├── .github/workflows/     # develop PR·push 자동 검증
├── docs/                  # 세션 규약·실제 연결 검증·CI 안내
├── frontend/              # React 키오스크
├── backend/               # Spring Boot API 및 WebSocket 중계
├── server/                # Python 추론 서버와 모델
├── docker-compose.yml
├── GIT_CONVENTION.md
└── README.md
```

모듈별 상세 문서는 아래에서 확인할 수 있습니다.

- [Frontend README](frontend/README.md)
- [Backend README](backend/README.md)
- [AI Server README](server/README.md)
- [배포 모델 README](server/deployment/README.md)
- [추론 테스트 README](server/tests/INFERENCE_TEST_README.md)
- [Git Convention](GIT_CONVENTION.md)
- [실시간 인식 WebSocket 규약 v1](docs/RECOGNITION_PROTOCOL.md)
- [실제 ONNX 연결 검증과 카메라 확인 기록](docs/LIVE_RECOGNITION_CHECK.md)
- [자동 검증(CI) 범위와 실행 결과](docs/CI.md)

## 로컬 실행

### 요구 사항

- Node.js 24 권장 (로컬 검증·CI 기준)
- JDK 17 및 Gradle 8.14.4
- Python 3.10 권장
- 카메라를 사용할 수 있는 브라우저

세 모듈은 각각 별도 터미널에서 실행합니다. AI 서버의 모델 경로가 상대 경로이므로 Python 명령은 반드시 `server` 디렉터리에서 실행해야 합니다.

저장소에는 `gradle-wrapper.jar`가 없으므로 아래에서는 별도 설치한 `gradle`을 사용합니다. 프론트 Vite의 Node 요구 범위는 `^20.19.0 || >=22.12.0`이며 세션 테스트에는 Node의 TypeScript 직접 실행 기능도 필요하므로 Node 24로 맞추는 것을 권장합니다.

### 1. AI 추론 서버

```bash
cd server
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install torch==2.14.0+cpu --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-smoke.txt
python -m pip check
python ai_server.py
```

위 명령은 Windows CPU에서 확인한 웹 추론 최소 의존성 설치 예시입니다. Linux/macOS 가상환경 활성화는 `source .venv/bin/activate`를 사용하며, PyTorch 패키지는 플랫폼에 맞게 선택하고 설치 호환성을 별도 확인해야 합니다. 학습·로컬 MediaPipe 용도의 전체 `requirements.txt` 설치는 이번 연결 검증에 포함되지 않았습니다. 로컬 주소에만 바인딩하고 디버그 모드 없이 실행하는 방법은 [검증 절차](docs/LIVE_RECOGNITION_CHECK.md)를 참고합니다.

AI 서버는 `http://localhost:5001`에서 실행되며 다음 인터페이스를 제공합니다.

- `POST /predict_keypoints`
- `WS /ws/predict`

### 2. 백엔드

Windows:

```powershell
cd backend
gradle bootRun
```

macOS/Linux:

```bash
cd backend
gradle bootRun
```

백엔드는 `http://localhost:8080/api`에서 실행됩니다.

- Health check: `http://localhost:8080/api/health/ping`
- Swagger UI: `http://localhost:8080/api/swagger-ui.html`
- H2 Console: `http://localhost:8080/api/h2-console`

### 3. 프론트엔드

```bash
cd frontend
npm ci
npm run dev
```

Vite 개발 서버가 출력하는 주소로 접속합니다. 기본 인식 WebSocket 주소는 `ws://localhost:8080/api/sign/stream`입니다.

다른 백엔드 주소를 사용하려면 `frontend/.env.local`을 생성합니다.

```dotenv
VITE_RECOGNITION_SERVER_URL=ws://localhost:8080/api/sign/stream
```

HTTP API 주소는 현재 `frontend/src/api/axios.ts`에 `http://localhost:8080/api`로 고정되어 있습니다.

## Docker Compose

Docker 설정 파일은 있지만 현재 CI는 Docker 이미지나 Compose 기동을 검증하지 않습니다. 아래 명령을 사용하기 전에 다음 제한을 확인해야 합니다.

```bash
docker compose up --build
```

기본 포트는 Frontend `80`, Backend `8080`, AI Server `5001`입니다.

현재 `docker-compose.yml`에는 AI 서버의 NVIDIA GPU 예약이 설정되어 있습니다. GPU가 없는 환경에서 기동이 실패하면 `ai-server.deploy.resources.reservations.devices` 블록을 제거해야 합니다. 또한 컨테이너 환경에서는 백엔드의 AI 연결 주소가 각각 `ws://ai-server:5001/ws/predict`, `http://ai-server:5001/predict_keypoints`가 되어야 합니다.

- 백엔드 Dockerfile은 `gradle build -x test`로 생성한 `*.jar`를 단일 `app.jar`로 복사합니다. 현재 빌드는 실행 JAR와 plain JAR를 모두 생성하므로 실행 JAR만 선택하도록 수정해야 합니다.
- AI Dockerfile은 최소 의존성이 아닌 전체 `requirements.txt`를 설치합니다. 위 CPU 연결 검증 결과를 Docker 설치 성공으로 해석하면 안 됩니다.
- 프론트 Dockerfile은 Node 20 및 `npm install`을 사용합니다. Node 24·`npm ci`를 사용하는 CI와 환경이 다르며, 다른 PC에서 접속할 경우 소스의 `localhost` API 주소와 빌드 시 WebSocket 주소도 조정해야 합니다.

## 검증 명령

`develop` 대상 PR과 `develop` push에서 FE·BE·AI 세션 검사를 실행하도록 [GitHub Actions CI](docs/CI.md)를 구성했습니다. 실제 모델·카메라 검증은 별도입니다.

```bash
cd frontend
npm run lint -- --max-warnings 0
npm test
npm run build
```

```bash
cd backend
gradle --no-daemon --console=plain clean build
```

```bash
cd server
python -S -m unittest tests.test_sessions -v
```

2026-09-22 로컬 및 [PR CI](https://github.com/doukdoll/sign_language_ver.2/actions/runs/35729782219), [develop 병합 후 CI](https://github.com/doukdoll/sign_language_ver.2/actions/runs/35732788235)에서 FE·BE·AI 작업이 모두 통과했습니다. 로컬 테스트 수는 FE 8개, BE 16개, AI 세션 15개이며 FE lint 오류·경고는 0개입니다.

실제 모델을 사용하는 별도 테스트는 [추론 테스트 README](server/tests/INFERENCE_TEST_README.md)를 참고합니다.

## 현재 확인된 제한 사항

- 실시간 인식은 WebSocket v1 세션 규약을 사용합니다. 실제 ONNX 연결은 합성 입력으로 검증했고 카메라 확인은 PR #15 시점의 소유자 확인 기록이 있습니다. PR #17의 카메라 정리 변경 이후 수동 재검증과 모델 정확도 평가는 별도입니다.
- AI 입력 정책 비교는 원본 수어 영상 확보 대기 상태입니다. 현재 128프레임 수집·180프레임 모델 입력 정책은 유지합니다.
- 승객 수, 편도·왕복, 날짜·시간, 좌석 등급용 REST 인식 API는 실제 모델 추론이 아니라 고정 응답을 반환합니다.
- 시간표 조회 오류나 빈 결과가 발생하면 프론트는 2025년 기준 mock 데이터를 표시합니다.
- 결제 화면은 시뮬레이션이며 실제 결제 승인이나 백엔드 저장을 수행하지 않습니다.
- 화면 간 데이터는 React Router의 `location.state`로 전달되므로 중간 페이지를 새로고침하면 상태가 사라질 수 있습니다.
- 2026-09-22 `npm ci`에서 기존 취약점 19개가 보고됐고, 프론트 번들 크기 경고도 남아 있습니다. CI 통과가 보안 검사나 운영 배포 검증을 의미하지는 않습니다.

## 라이선스

이 프로젝트는 [MIT License](LICENSE)를 따릅니다.
