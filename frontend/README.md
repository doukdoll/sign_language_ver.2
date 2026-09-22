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

현재 인식 경로는 [WebSocket 규약 v1](../docs/RECOGNITION_PROTOCOL.md)을 사용합니다. 기존 START/FRAME 메시지만 보내는 클라이언트와는 호환되지 않습니다.

```text
Camera → useHolistic → buildKeypoints137 → useKeypointStreaming
       → Backend /api/sign/stream → AI /ws/predict
```

- START에 브라우저 임의 ID를 넣지 않습니다. AI의 SESSION_STARTED가 중계되면 BE가 부여한 ID를 저장하고 프레임을 보냅니다.
- 출발/도착 화면은 각각 DEPARTURE/ARRIVAL을 명시합니다.
- 키포인트는 137 × 3 [x, y, confidence]이고 결측점은 [null, null, 0]입니다.
- 다시 인식하기는 RESET_SESSION을 전송합니다. revision을 올려 이전 결과를 즉시 무효화하고, SESSION_RESET 이후 frameIndex 0부터 보냅니다.
- RESULT의 ID·revision·대상·frameIndex를 검사합니다. 도시 필드는 대상에 맞는 것만 표시하고 <unk>는 확정할 수 없습니다.
- 연결 종료/오류 시 기존 결과를 지우며, 새 연결에서 새 ID로 다시 시작합니다. 재접속 간격은 1~10초, START/RESET ACK 대기 제한은 10초입니다.
- 페이지 이탈 시 END를 최선 노력으로 보낸 뒤 소켓을 닫습니다. BE의 연결 종료 처리도 해당 AI 세션을 정리합니다.

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
| `npm run build` | TypeScript 검사 후 Vite 프로덕션 빌드 |
| `npm run typecheck` | 앱·Vite 설정의 TypeScript 검사 |
| `npm test` | Node.js 22.6+에서 카메라 없는 세션 규약 회귀 테스트 |
| `npm run test:recognition:live` | 실행 중인 실제 BE·Python·ONNX에 합성 키포인트를 전송하는 연결 검사 |
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

- 백엔드 API 주소가 환경변수가 아닌 소스 코드에 고정되어 있습니다.
- 시간표 API 실패가 mock 데이터로 숨겨져 연결 오류를 UI에서 알아보기 어렵습니다.
- 결제와 좌석 재고는 프론트 전용 시뮬레이션입니다.
- 페이지 간 `location.state`와 API 응답은 런타임 스키마 검증을 하지 않으며, 일부 화면에 임시 콘솔 로그가 남아 있습니다.

## 현재 검증 결과

실제 서버 연결 검증과 카메라 확인 절차는 [실행 기록](../docs/LIVE_RECOGNITION_CHECK.md)을 참고합니다. 합성 데이터 연결 성공은 인식 정확도 평가가 아닙니다.

2026-09-22 기준으로 로컬에서 확인한 결과입니다.

- `npm run lint -- --max-warnings 0`: 전체 프론트 오류 0개 / 경고 0개.
- `npm run typecheck`: 성공. 기존 미사용 변수 타입 오류 11개를 정리했습니다.
- `npm run build`: 타입 검사와 프로덕션 빌드 성공. 메인 JavaScript chunk가 500 kB를 넘어 분할 경고가 발생하며, 브라우저 호환성 데이터 갱신 안내가 남아 있습니다.
- `npm test`: 세션 규약 테스트 8개 통과(Node.js 24).
- 이번 정리 후 실제 카메라 화면과 결제 완료·취소 흐름의 수동 검증은 아직 수행하지 않았습니다. 세션 규약 테스트는 이 UI 동작을 검증하지 않습니다.

의존성 설치·보안 검사는 이번 작업에서 다시 실행하지 않았습니다. 이전 2026-09-17 검사에서는 `npm ci`가 성공했고 npm audit 취약점 19개가 보고됐습니다.
