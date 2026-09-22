# Frontend API & WebSocket 연동 명세

현재 `frontend/src/` 구현 기준입니다. 실행과 검증 명령은 [Frontend README](frontend/README.md), 서버 API 상세는 [Backend API 명세](BACKEND_API_DOCS.md), WebSocket의 전체 계약은 [실시간 인식 규약 v1](docs/RECOGNITION_PROTOCOL.md)을 참고하세요.

## 1. HTTP REST API

공통 Axios 인스턴스는 `frontend/src/api/axios.ts`에 있으며 `baseURL`은 `http://localhost:8080/api`로 고정되어 있습니다. 아래 경로는 이 주소에 이어 붙입니다.

### 선택값 전달

| 화면 | 요청 | `signLanguageData` 예시 | `recognitionTarget` |
| --- | --- | --- | --- |
| `PassengerPage.tsx` | `POST /signlanguage/passengers` | `"2"` | `passengers` |
| `TripTypePage.tsx` | `POST /signlanguage/triptype` | `"one-way"` 또는 `"round"` | `triptype` |
| `DateTimePage.tsx` | `POST /signlanguage/datetime` | `"2026-09-22 09:00"` | `datetime` |

요청 형식:

```json
{
  "signLanguageData": "2",
  "recognitionTarget": "passengers"
}
```

왕복 날짜는 `2026-09-22 09:00 | 2026-09-24 18:00`처럼 전달합니다. 세 API는 현재 **고정 응답**을 반환하며 선택값을 저장하거나 AI로 해석하지 않습니다. FE는 응답을 로그로 확인하고, 사용자가 고른 값을 React Router의 `location.state`로 다음 화면에 전달합니다. 고정 응답으로 사용자 선택을 덮어쓰지 않습니다.

### 기차 시간표 조회

`TrainTimeTablePage.tsx`가 `GET /train/search`에 다음 query parameter를 보냅니다.

| 필드 | 예시 |
| --- | --- |
| `departure` | `서울` |
| `destination` | `부산` |
| `departureFrom` | `2026-09-22 09:00` (`yyyy-MM-dd HH:mm`, 초 없음) |

조회 결과가 없거나 요청이 실패한 경우, 또는 코드가 필수 입력 누락으로 판정한 경우에는 현재 화면이 하드코딩된 mock 시간표를 표시합니다. 표시된 열차가 실제 API 조회 성공을 뜻하지 않습니다. 서버의 요금·좌석 잔여 수 자체도 프로토타입 값입니다.

### 이전 REST 인식 훅과 미연결 API

`useStationRecognition.ts`는 `POST /signlanguage/recognize`에 가짜 제스처와 `recognitionTarget: "city"`를 보내는 이전 테스트 훅입니다. 현재 출발역·도착역 페이지는 이 훅을 사용하지 않습니다. 서버가 `city`를 유효한 인식 대상으로 처리하지 않으므로 실제 인식 예제로 사용하지 않습니다.

BE에는 `/booking/train` API가 있지만 현재 FE는 이를 호출하지 않습니다. 좌석 선택·결제·티켓 완료 화면은 실제 좌석 재고, 결제 승인, 예약 저장과 연결되지 않은 시뮬레이션입니다.

## 2. WebSocket 기반 실시간 인식

- 화면: `DeparturePage.tsx` (`DEPARTURE`), `ArrivalPage.tsx` (`ARRIVAL`)
- 기본 URL: `ws://localhost:8080/api/sign/stream`
- URL 변경: Vite 환경변수 `VITE_RECOGNITION_SERVER_URL` (개발 서버 시작 또는 빌드 시 적용)
- 상태/메시지 검증: `frontend/src/utils/recognitionSession.ts`
- 소켓·ACK 제한 시간·재접속: `frontend/src/hooks/useKeypointStreaming.ts`
- MediaPipe와 인식 UI 연결: `frontend/src/hooks/useRecognitionFlow.ts`

### 세션 시작

FE는 소켓 연결 후 **ID 없이** 다음 요청을 보냅니다. BE가 실제 연결의 ID를 할당합니다.

```json
{
  "protocolVersion": 1,
  "type": "START_SESSION",
  "revision": 0,
  "recognitionTarget": "DEPARTURE",
  "timestamp": 1789600000000
}
```

`SESSION_STARTED`의 ID를 저장하고 ACK를 받은 뒤에만 프레임을 보냅니다. 소켓 연결 성공만으로 인식 준비 완료 상태가 되지는 않습니다.

### 키포인트 전송

MediaPipe 결과를 Pose 25개·Face 70개·왼손 21개·오른손 21개의 순서로 변환합니다. 각 점은 `[x, y, confidence]`이며 결측값은 `[null, null, 0]`입니다. x/y는 영상 크기 기준 좌표, confidence는 0~1입니다. 274차원 모델 입력 생성은 AI가 담당합니다.

아래는 137 × 3 크기를 갖춘 진단용 요청입니다. 실제 수어 데이터가 아닌 모두 결측인 예시입니다.

```javascript
const frame = {
  protocolVersion: 1,
  type: "KEYPOINT_FRAME",
  sessionId: "spring-session-a",
  revision: 0,
  recognitionTarget: "DEPARTURE",
  timestamp: 1789600000033,
  frameIndex: 0,
  keypoints: Array.from({ length: 137 }, () => [null, null, 0]),
};
```

두 인식 페이지의 목표 전송 상한은 30 FPS이며 손 감지 필터를 사용합니다. 실제 프레임 수는 카메라·MediaPipe 처리 속도와 필터에 따라 달라집니다. `frameIndex`는 revision마다 0부터 증가합니다.

### 결과 수신과 확정

```json
{
  "protocolVersion": 1,
  "type": "RESULT",
  "sessionId": "spring-session-a",
  "revision": 0,
  "recognitionTarget": "DEPARTURE",
  "timestamp": 1789600005000,
  "frameIndex": 127,
  "departureCity": "서울",
  "arrivalCity": null,
  "recognizedProb": 95.0
}
```

확률은 **0~100 백분율**이며 예시는 품질 측정값이 아닙니다. ARRIVAL 결과는 `arrivalCity`만 문자열이고 `departureCity`는 null입니다. FE는 현재 ID·revision·대상과 프레임 순서를 검증합니다. 필수 envelope가 없는 이전 DTO나 `label` 응답을 fallback으로 처리하지 않습니다.

`<unk>`는 확정 가능한 역으로 표시하지 않습니다. 인식 준비 상태와 유효 결과를 모두 만족해야 확인 버튼이 활성화되며, 사용자가 확정한 역을 다음 페이지의 router state로 전달합니다.

### 재시도·오류·종료

- 재시도는 결과를 지우고 `RESET_SESSION`을 revision + 1로 전송합니다. `SESSION_RESET` 이후 frameIndex 0부터 재개합니다.
- START/RESET ACK 제한 시간은 10초입니다. 실패·연결 종료 시 오류를 표시하고 1초부터 최대 10초 간격으로 재접속합니다.
- 재접속은 새 서버 발급 ID와 revision 0으로 시작하며 이전 버퍼를 복원하지 않습니다.
- 화면을 떠나거나 인식을 중지하면 `END_SESSION`을 최선 노력으로 전송하고 소켓을 닫습니다.
- 카메라 컴포넌트가 사라지면 자신이 연 스트림의 트랙을 종료합니다. 권한 응답이 늦게 도착한 경우도 종료 처리합니다.

## 3. 검증 범위

[CI](.github/workflows/ci.yml)는 `develop` 대상 PR과 push에서 FE 전체 lint(경고 0), 세션 회귀 테스트 8개, 타입 검사와 프로덕션 빌드를 수행합니다. 이 테스트는 순수 세션 상태 로직을 검증하며 React 화면·카메라·실제 결제를 자동 검증하지 않습니다.

FE 세션 코드 → 실제 BE → Python → ONNX 스모크 명령 및 브라우저 확인 항목은 [실시간 연동 검증 문서](docs/LIVE_RECOGNITION_CHECK.md)를 참고하세요.
