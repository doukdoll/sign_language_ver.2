# Frontend

수어로 출발역과 도착역을 입력하고 기차 조회, 좌석 선택, 결제 완료 화면까지 진행하는 450×900 키오스크 UI입니다.

## 기술 스택

- React 19.1
- TypeScript 5.9
- Vite 7
- React Router DOM 7.9
- Tailwind CSS 4
- Axios
- MediaPipe Holistic, Camera Utils
- React Webcam
- React Datepicker

## 주요 기능

- 브라우저 카메라에서 MediaPipe Holistic 실행
- MediaPipe 랜드마크를 OpenPose 순서의 137개 키포인트로 변환
- 손 랜드마크가 있는 프레임을 백엔드 WebSocket으로 전송
- 출발역과 도착역 인식 결과 확인·재시도
- 승객 수와 편도·왕복 선택
- 날짜와 시간 선택
- 백엔드 열차 시간표 검색
- 좌석 선택과 예매 내역 확인
- 카드·네이버페이 결제 화면 시뮬레이션

## 실행

### 요구 사항

- Node.js 20 이상 권장
- npm
- 카메라 권한을 허용할 수 있는 브라우저
- HTTP API용 Spring Boot 서버
- 실시간 역 인식용 WebSocket 서버

```bash
npm ci
npm run dev
```

Vite가 출력하는 로컬 주소로 접속합니다. 카메라 API는 보안 컨텍스트가 필요하므로 개발 중에는 `localhost`를 사용해야 합니다.

## 환경 설정

실시간 키포인트 전송 주소는 `VITE_RECOGNITION_SERVER_URL`로 바꿀 수 있습니다.

`frontend/.env.local`:

```dotenv
VITE_RECOGNITION_SERVER_URL=ws://localhost:8080/api/sign/stream
```

변수가 없으면 코드의 기본값 `ws://localhost:8080/api/sign/stream`을 사용합니다. Vite 환경변수는 빌드 시점에 삽입되므로 값을 바꾼 뒤 개발 서버나 Docker 이미지를 다시 빌드해야 합니다.

REST API base URL은 현재 `src/api/axios.ts`에 아래 값으로 고정되어 있습니다.

```text
http://localhost:8080/api
```

## 사용자 흐름과 라우트

| 경로 | 화면 | 전달되는 주요 상태 |
| --- | --- | --- |
| `/` | 시작 화면 | 없음 |
| `/departure` | 출발역 수어 인식 | 인식된 출발역 |
| `/arrival` | 도착역 수어 인식 | 출발역, 인식된 도착역 |
| `/passenger` | 승객 수 선택 | 출발역, 도착역, 승객 수 |
| `/triptype` | 편도·왕복 선택 | 여정 유형 |
| `/datetime` | 출발·복귀 일시 선택 | 날짜와 시간 |
| `/timetable` | 열차 시간표 선택 | 선택 열차 |
| `/seat` | 좌석 선택 | 선택 좌석 |
| `/summary` | 예매 정보 확인 | 전체 예매 상태 |
| `/payment` | 결제 진행 시뮬레이션 | 결제 수단과 금액 |
| `/paymentcomplete` | 결제 완료 | 최종 표시 정보 |

페이지 데이터는 전역 store나 서버 세션이 아니라 React Router의 `location.state`로 전달됩니다. 중간 화면에서 새로고침하거나 URL로 직접 접근하면 이전 단계의 정보가 없어질 수 있습니다.

## 실시간 인식 흐름

다음 구현에서 사용할 메시지 기준은 [WebSocket 규약 v1](../docs/RECOGNITION_PROTOCOL.md)입니다. 아래 내용은 현재 구현을 설명합니다.

```text
CameraFeed
  └─ useHolistic
       └─ buildKeypoints137
            └─ hasValidHands
                 └─ useKeypointStreaming
                      └─ ws://localhost:8080/api/sign/stream
```

### WebSocket 송신

연결 직후:

```json
{
  "type": "START_SESSION",
  "sessionId": "session-...",
  "timestamp": 0,
  "recognitionTarget": "DEPARTURE"
}
```

키포인트 프레임:

```json
{
  "type": "KEYPOINT_FRAME",
  "sessionId": "session-...",
  "timestamp": 0,
  "frameIndex": 0,
  "keypoints": [[0.0, 0.0]],
  "recognitionTarget": "DEPARTURE"
}
```

`keypoints`에는 Pose 25개, Face 70개, 왼손 21개, 오른손 21개가 순서대로 들어갑니다. 실제 변환 함수는 각 점을 `[x, y, confidence]` 형식으로 생성합니다. 위의 축약 예시와 달리 실제 전송은 137 × 3 배열입니다.

### WebSocket 수신

현재 클라이언트가 인식하는 주요 응답 필드는 다음과 같습니다.

```json
{
  "departureCity": "서울역",
  "arrivalCity": null,
  "recognizedProb": 98.7
}
```

`recognitionTarget`이 `DEPARTURE`이면 `departureCity`, `ARRIVAL`이면 `arrivalCity`를 화면에 표시합니다. `type: "RESULT"`와 `label` 형식도 fallback으로 처리합니다.

## 열차 조회

`TrainTimeTablePage`는 다음 API를 호출합니다.

```http
GET /api/train/search
```

전송 값:

- `departure`
- `destination`
- `departureFrom`: `yyyy-MM-dd HH:mm`

필수 화면 상태가 없거나 API 오류·빈 결과가 발생하면 코드에 포함된 2025년 mock 시간표 두 건을 대신 표시합니다. 따라서 화면에 열차가 보인다는 사실만으로 백엔드 연결 성공을 판단하면 안 됩니다.

## 결제 동작

결제는 실제 API 호출이 아니라 UI 시뮬레이션입니다.

1. 예매 요약 화면에서 결제 수단을 선택합니다.
2. 결제 화면이 6초 동안 진행 상태를 표시합니다.
3. 자동으로 결제 완료 화면으로 이동합니다.

현재 `POST /api/booking/train`이나 결제 백엔드 API를 호출하지 않습니다.

## 스크립트

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Vite 개발 서버 실행 |
| `npm run build` | Vite 프로덕션 빌드 |
| `npm run lint` | ESLint 검사 |
| `npm run preview` | 빌드 결과 로컬 미리보기 |

## Docker

```bash
docker build -t sign-language-frontend .
docker run --rm -p 80:80 sign-language-frontend
```

이미지는 Node 20에서 빌드한 정적 파일을 Nginx로 제공합니다. `nginx.conf`는 React Router 경로를 `index.html`로 fallback하도록 구성되어 있습니다.

## 주요 구조

```text
src/
├── api/                 # Axios 인스턴스와 REST 호출
├── assets/              # 이미지 리소스
├── components/          # 공통 UI, 카메라, 좌석 컴포넌트
├── hooks/               # MediaPipe와 WebSocket 인식 흐름
├── pages/               # 키오스크 단계별 화면
├── styles/              # 달력·좌석 스타일
├── utils/               # MediaPipe → OpenPose 변환
├── App.tsx              # 라우트 정의
└── main.tsx             # React 진입점
```

## 현재 제한 사항

- `useRecognitionFlow`의 옵션 타입과 내부 전달 로직에 `recognitionTarget`이 없어 현재 도착역 화면도 기본값 `DEPARTURE`로 전송합니다.
- `useRecognitionFlow`의 스트리밍 상태 동기화에 `useState`가 사용되어 있어 의도한 반응형 갱신이 되지 않을 수 있습니다.
- 백엔드 API 주소가 환경변수가 아닌 소스 코드에 고정되어 있습니다.
- 시간표 API 실패가 mock 데이터로 숨겨져 연결 오류를 UI에서 알아보기 어렵습니다.
- 결제와 좌석 재고는 프론트 전용 시뮬레이션입니다.
- 일부 화면은 `any` 타입과 임시 콘솔 로그를 사용합니다.

## 현재 검증 결과

2026-09-17 기준으로 잠금 파일을 사용해 확인한 결과입니다.

- `npm ci`: 성공. npm audit 기준 취약점 19개가 보고됩니다.
- `npm run build`: 성공. 메인 JavaScript chunk가 500 kB를 넘어 분할 경고가 발생합니다.
- `npm run lint`: 실패. 사용하지 않는 변수, `any` 타입, Hook dependency 등 17 errors / 8 warnings가 남아 있습니다.
