# Frontend API & WebSocket 연동 명세

현재 `frontend/src/` 구현 기준입니다. 실행과 검증 명령은 [Frontend README](frontend/README.md), 서버 API 상세는 [Backend API 명세](BACKEND_API_DOCS.md), WebSocket의 전체 계약은 [실시간 인식 규약 v1](docs/RECOGNITION_PROTOCOL.md)을 참고하세요.

## 1. HTTP REST API

공통 Axios 인스턴스는 `frontend/src/api/axios.ts`에 있으며 `baseURL`은 `http://localhost:8080/api`로 고정되어 있습니다. 아래 경로는 이 주소에 이어 붙입니다.

### 수동 선택값 전달

`PassengerPage.tsx`, `TripTypePage.tsx`, `DateTimePage.tsx`에서 선택한 값은 React Router의 `location.state`로 다음 화면에 전달합니다. 이 단계에는 HTTP 요청이 없습니다. 이전에 호출하던 `/signlanguage/passengers`, `/signlanguage/triptype`, `/signlanguage/datetime`은 고정 응답만 반환하고 선택값을 저장하지 않아 FE 호출을 제거했습니다. BE의 기존 REST 경로는 유지합니다.

`src/utils/reservation.ts`는 역·승객 수·여정 종류·일시·열차·좌석 필드를 검증합니다. 필수 정보가 없는 예약 단계는 시작 화면으로 돌아갑니다. 왕복 선택 중에는 `seats1`과 `selectedTrain1`을 유지한 채 오는 편의 `seats2`와 `selectedTrain2`를 추가합니다. 요약 화면은 두 편을 표시하고 두 운임 합계에 승객 수를 곱합니다. 미완성 왕복 상태를 편도 금액으로 결제하지 않습니다.

열차 경로 검증은 백엔드의 검색어 공백 제거와 `대구 → 동대구/서대구` 검색 별칭을 허용합니다. 열차 선택 이후의 상태는 실제 열차 출발·도착역으로 갱신합니다. 왕복은 그 실제 구간을 뒤집어 조회하며 `동대구`를 명시한 검색에서 `서대구` 열차를 임의로 허용하지 않습니다.

### 기차 시간표 조회

`TrainTimeTablePage.tsx`가 `GET /train/search`에 다음 query parameter를 보냅니다.

| 필드 | 예시 |
| --- | --- |
| `departure` | `서울` |
| `destination` | `부산` |
| `departureFrom` | `2026-09-22 09:00` (`yyyy-MM-dd HH:mm`, 초 없음) |

`src/utils/trainSchedules.ts`에서 응답 배열과 각 열차의 화면 사용 필드를 검증합니다. 빈 결과는 빈 목록 안내, 요청 실패·잘못된 응답은 오류와 재조회 버튼으로 표시합니다. 필수 입력 누락 시 시작 화면으로 돌아가며 mock 시간표를 대신 표시하지 않습니다. 운임이 `null`인 열차는 선택 완료가 차단됩니다.

검색 시작 시 이전 결과와 선택을 초기화합니다. 요청에는 `AbortSignal`을 전달하며 화면 이탈·조건 변경 시 취소하고, 취소 후 도착한 성공·실패 응답은 무시합니다. 백엔드 CSV·요금·좌석 잔여 수는 여전히 프로토타입 데이터이며 실시간 철도 판매 시스템은 아닙니다.

### 미연결 API

가짜 제스처를 보내던 `useStationRecognition.ts`와 임의 인식 결과를 반환하던 `UseRecognition.ts`는 사용되지 않아 삭제했습니다. 현재 FE의 역 인식은 아래 WebSocket 경로만 사용하며 `/signlanguage/recognize`를 호출하지 않습니다.

BE에는 `/booking/train` API가 있지만 현재 FE는 이를 호출하지 않습니다. 좌석 선택·결제·티켓 완료 화면은 실제 좌석 재고, 결제 승인, 예약 저장과 연결되지 않은 시뮬레이션입니다.

## 2. WebSocket 기반 실시간 인식

- 화면: `DeparturePage.tsx` (`DEPARTURE`), `ArrivalPage.tsx` (`ARRIVAL`)
- 기본 URL: `ws://localhost:8080/api/sign/stream`
- URL 변경: Vite 환경변수 `VITE_RECOGNITION_SERVER_URL` (개발 서버 시작 또는 빌드 시 적용)
- 상태/메시지 검증: `frontend/src/utils/recognitionSession.ts`
- 소켓·ACK 제한 시간·재접속: `frontend/src/hooks/useKeypointStreaming.ts`
- MediaPipe와 인식 UI 연결: `frontend/src/hooks/useRecognitionFlow.ts`
- 카메라 단일 소유·처리 루프: `frontend/src/hooks/useHolistic.ts`, `frontend/src/utils/cameraPipeline.ts`

`CameraFeed`는 `<video>` 표시만 담당합니다. `useHolistic`이 브라우저 `getUserMedia` 스트림과 MediaPipe 인스턴스를 소유하며 프레임을 순차 처리합니다. 기존 Camera Utils의 별도 스트림 요청은 제거했고, 사용하지 않던 React Webcam 의존성도 삭제했습니다.

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
- 카메라 오류가 있으면 재시도 시 카메라·MediaPipe 초기화도 다시 수행합니다. 카메라 재시작과 서버 세션의 revision 처리는 별개입니다.
- START/RESET ACK 제한 시간은 10초입니다. 실패·연결 종료 시 오류를 표시하고 1초부터 최대 10초 간격으로 재접속합니다.
- 재접속은 새 서버 발급 ID와 revision 0으로 시작하며 이전 버퍼를 복원하지 않습니다.
- 화면을 떠나거나 인식을 중지하면 `END_SESSION`을 최선 노력으로 전송하고 소켓을 닫습니다.
- 인식을 중지하거나 화면을 떠나면 소유한 카메라 트랙과 프레임 루프를 종료합니다. 권한 응답이 늦게 도착한 경우에도 트랙을 종료하고, 초기화·프레임 처리 중 이탈한 경우에는 해당 처리가 끝난 뒤 MediaPipe를 닫으며 늦은 결과를 전달하지 않습니다.

## 3. 검증 범위

[CI](.github/workflows/ci.yml)는 `develop` 대상 PR과 push에서 FE 전체 lint(경고 0), `npm test`, 타입 검사와 프로덕션 빌드를 수행합니다. 과거 PR #18 및 당시 develop CI 통과는 세션 테스트 8개 기준 기록입니다.

이번 코드 정리 후 로컬 lint·타입 검사·빌드와 테스트 34개(세션 규약 8개, 모의 카메라 생명주기 11개, 예약/조회 15개)가 통과했습니다. 원격 CI는 [PR #20](https://github.com/doukdoll/sign_language_ver.2/pull/20)의 최종 커밋 Checks를 확인합니다. 실제 브라우저 수동 재검증은 남아 있습니다. 테스트는 주입한 모의 카메라/스케줄러·순수 상태·비동기 요청을 검증하며 실제 장치·MediaPipe WASM·React 화면·결제를 자동 실행하지 않습니다.

FE 세션 코드 → 실제 BE → Python → ONNX 스모크 명령 및 브라우저 확인 항목은 [실시간 연동 검증 문서](docs/LIVE_RECOGNITION_CHECK.md)를 참고하세요.
