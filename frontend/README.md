# Frontend

수어로 출발역과 도착역을 입력하고 기차 조회, 좌석 선택, 결제 완료 화면까지 진행하는 450×900 키오스크 UI입니다.

## 기술 스택

- React 19.1
- TypeScript 5.9
- Vite 7
- React Router DOM 7.9
- Tailwind CSS 4
- Axios
- MediaPipe Holistic, 브라우저 MediaDevices API
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

- Node.js 24 권장 (로컬 검증·CI 기준; Vite 요구 범위는 `^20.19.0 || >=22.12.0`)
- npm
- 카메라 권한을 허용할 수 있는 브라우저
- HTTP API용 Spring Boot 서버
- 실시간 역 인식용 WebSocket 서버

```bash
npm ci
npm run dev
```

Vite가 출력하는 로컬 주소로 접속합니다. 카메라는 보안 컨텍스트에서 사용하며 로컬 검증에는 `localhost` 또는 `127.0.0.1`을 사용합니다. 다른 장치의 일반 HTTP 주소로 접속하는 배포 방식은 별도 점검이 필요합니다.

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

페이지 데이터는 전역 store나 서버 세션이 아니라 React Router의 `location.state`로 전달됩니다. 승객 수·편도/왕복·날짜 선택은 로컬 상태로 전달하며, 고정 응답만 반환하던 REST API를 기다리지 않습니다. 예약 단계의 공통 타입과 입력 검증은 `src/utils/reservation.ts`에 있습니다. 필수 정보가 없는 승객·여정·날짜·시간표·좌석·요약 화면 접근은 시작 화면으로 돌려보냅니다.

왕복은 가는 편 좌석 선택 후 출발·도착역과 검색 일시를 복귀 조건으로 전환합니다. 가는 편 열차·좌석을 유지하면서 오는 편을 추가하고, 예매 요약에는 두 편을 모두 표시합니다. 총액은 두 편의 1인 운임 합계 × 승객 수로 계산합니다. 각 편의 좌석 수가 승객 수와 일치해야 다음 단계로 진행할 수 있습니다.

백엔드와 동일하게 `대구` 검색으로 반환되는 `동대구`·`서대구` 열차를 선택할 수 있습니다. 선택 이후에는 열차의 실제 역 이름을 저장하며 왕복 검색도 그 실제 구간을 반전합니다. 예를 들어 `서울 → 대구` 검색에서 `서울 → 동대구` 열차를 고르면 복귀 구간은 `동대구 → 서울`입니다.

## 실시간 인식 흐름

현재 인식 경로는 [WebSocket 규약 v1](../docs/RECOGNITION_PROTOCOL.md)을 사용합니다. 기존 START/FRAME 메시지만 보내는 클라이언트와는 호환되지 않습니다.

```text
Camera → useHolistic → buildKeypoints137 → useKeypointStreaming
       → Backend /api/sign/stream → AI /ws/predict
```

- START에 브라우저 임의 ID를 넣지 않습니다. AI의 SESSION_STARTED가 중계되면 BE가 부여한 ID를 저장하고 프레임을 보냅니다.
- 출발/도착 화면은 각각 DEPARTURE/ARRIVAL을 명시합니다.
- 키포인트는 137 × 3 [x, y, confidence]이고 결측점은 [null, null, 0]입니다.
- `CameraFeed`는 영상 표시만 담당합니다. `useHolistic`이 `cameraPipeline`을 통해 카메라 스트림 하나와 MediaPipe 처리 루프를 소유하며 중복 카메라 요청을 하지 않습니다. 프레임 처리는 순차 실행하고, 이탈 시 루프·트랙을 종료하며 늦은 권한 응답·초기화 완료·결과 콜백도 정리합니다.
- 다시 인식하기는 RESET_SESSION을 전송합니다. revision을 올려 이전 결과를 즉시 무효화하고, SESSION_RESET 이후 frameIndex 0부터 보냅니다.
- 카메라 오류 상태에서 다시하기를 누르면 WebSocket 세션 재설정과 별도로 카메라·MediaPipe 초기화를 다시 시도합니다.
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

필수 화면 상태가 없으면 시작 화면으로 돌아갑니다. API 오류·잘못된 응답에는 오류와 재조회 버튼을, 빈 결과에는 해당 조건의 열차가 없다는 안내를 표시합니다. 하드코딩 시간표로 대체하지 않습니다. 재조회 시 이전 결과와 선택을 비우고, 화면 이탈·검색 조건 변경 시 요청을 취소하며 늦은 응답은 무시합니다. 운임이 없는 열차는 다음 단계로 진행할 수 없습니다.

이는 실제 운행·판매 시스템과의 연동을 뜻하지는 않습니다. 백엔드 CSV 시간표와 프로토타입 운임을 사용하며, 좌석 선택 화면의 임의 점유 상태는 데모입니다.

## 결제 동작

결제는 실제 API 호출이 아니라 UI 시뮬레이션입니다.

1. 예매 요약 화면에서 결제 수단을 선택합니다.
2. 결제 화면이 6초 동안 진행 상태를 표시합니다.
3. 300ms 페이드 후 자동으로 결제 완료 화면으로 이동합니다.

현재 `POST /api/booking/train`이나 결제 백엔드 API를 호출하지 않습니다.
결제 취소·화면 이탈 시 대기/이동 타이머를 정리합니다.

## 스크립트

| 명령 | 설명 |
| --- | --- |
| `npm run dev` | Vite 개발 서버 실행 |
| `npm run build` | TypeScript 검사 후 Vite 프로덕션 빌드 |
| `npm run typecheck` | 앱·Vite 설정의 TypeScript 검사 |
| `npm test` | Node.js 22.6+에서 세션·카메라 생명주기·예약/조회 회귀 테스트 |
| `npm run test:recognition:live` | 실행 중인 실제 BE·Python·ONNX에 합성 키포인트를 전송하는 연결 검사 |
| `npm run lint` | ESLint 검사 |
| `npm run preview` | 빌드 결과 로컬 미리보기 |

## Docker

```bash
docker build -t sign-language-frontend .
docker run --rm -p 80:80 sign-language-frontend
```

이미지는 Node 20에서 빌드한 정적 파일을 Nginx로 제공합니다. `nginx.conf`는 React Router 경로를 `index.html`로 fallback하도록 구성되어 있습니다.
Dockerfile은 `npm install`을 사용하며 Node 24·`npm ci`로 검사하는 CI와 다릅니다. 현재 CI는 Docker 빌드·기동을 실행하지 않습니다.

## 주요 구조

```text
src/
├── api/                 # 공통 Axios 인스턴스
├── assets/              # 이미지 리소스
├── components/          # 공통 UI, 카메라, 좌석 컴포넌트
├── hooks/               # MediaPipe와 WebSocket 인식 흐름
├── pages/               # 키오스크 단계별 화면
├── styles/              # 달력·좌석 스타일
├── utils/               # 키포인트 변환, 세션/카메라 생명주기, 예약 상태·시간표 조회
├── App.tsx              # 라우트 정의
└── main.tsx             # React 진입점
```

## 현재 제한 사항

- 백엔드 API 주소가 환경변수가 아닌 소스 코드에 고정되어 있습니다.
- 결제와 좌석 재고는 프론트 전용 시뮬레이션입니다.
- 예약 정보는 `location.state`에만 있으며 영구 저장·예약 생성·결제 승인 API는 연결하지 않습니다.
- 예약 상태와 열차 응답은 사용 필드 중심으로 런타임 검증합니다. 전체 화면에 대한 브라우저 E2E 테스트는 아직 없습니다.

## 현재 검증 결과

실제 서버 연결 검증과 카메라 확인 절차는 [실행 기록](../docs/LIVE_RECOGNITION_CHECK.md)을 참고합니다. 합성 데이터 연결 성공은 인식 정확도 평가가 아닙니다.

아래는 2026-09-22 코드 정리 후 로컬 검사 결과입니다. 후속 [PR #20](https://github.com/doukdoll/sign_language_ver.2/pull/20)의 원격 결과는 Checks에서 확인합니다. 실제 브라우저·카메라 수동 재검증은 남아 있습니다. 과거 [CI](../docs/CI.md)의 PR #18 성공 기록은 당시 세션 테스트 8개 기준이며, 이번 변경의 최종 커밋 검증과 구분합니다.

- `npm run lint -- --max-warnings 0`: 전체 프론트 오류 0개 / 경고 0개.
- `npm run typecheck`: 성공. 기존 미사용 변수 타입 오류 11개를 정리했습니다.
- `npm run build`: 타입 검사와 프로덕션 빌드 성공. 메인 JavaScript chunk가 500 kB를 넘어 분할 경고가 발생하며, 브라우저 호환성 데이터 갱신 안내가 남아 있습니다.
- `npm test`: 34개 통과(Node.js 24). 세션 규약 8개, 모의 자원을 주입한 카메라 생명주기 11개, 예약 상태·시간표 요청 15개입니다.
- 예약 테스트는 편도·왕복 전달과 좌석 보존, 두 편 합산 금액, 불완전한 상태·운임·좌석 거부, 조회 취소·늦은 응답·빈 결과·오류·재시도를 검증합니다.
- 카메라 테스트는 중복 소유 방지, 권한 응답 지연, 초기화/프레임 처리 중 종료, 트랙 종료와 실패 정리를 검증합니다. 실제 장치·MediaPipe WASM·React 화면을 실행하는 테스트는 아닙니다. PR #15의 소유자 카메라 확인은 당시 구현에 대한 기록이며 이번 변경의 검증을 대신하지 않습니다.

2026-09-22 CI 구성 검증 중 `npm ci`를 다시 실행해 설치에 성공했습니다. 감사 요약에서 기존 취약점 19개(low 1, moderate 4, high 14)가 보고됐으며 의존성 자동 수정은 하지 않았습니다. CI는 별도의 보안 스캔을 포함하지 않습니다.
