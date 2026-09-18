# 실시간 수어 인식 WebSocket 규약 v1

상태: 실제 FE 세션 코드·BE·Python·ONNX 연결 검증 완료, 브라우저 카메라 검증 대기 (2026-09-18). [실행 기록과 재현 방법](LIVE_RECOGNITION_CHECK.md)

이 문서는 FE·BE·AI의 공통 규약이다. 세 구성 요소를 함께 적용해야 하며 이전 버전 메시지와는 호환되지 않는다. HTTP `/predict_keypoints`는 이번 규약의 대상이 아니다.

## 1. 연결과 세션 소유권

```text
Frontend A ─┐                         ┌─ A의 버퍼·인식 대상·revision
           ├─ Backend ── AI 연결 하나 ┤
Frontend B ─┘                         └─ B의 버퍼·인식 대상·revision
```

- FE → BE: `/api/sign/stream`
- BE → AI: `/ws/predict`
- 하나의 FE WebSocket 연결은 하나의 인식 세션을 소유한다.
- `sessionId`는 BE가 해당 FE WebSocket의 ID로 지정한다. FE가 임의로 지정한 ID로 다른 사용자에게 접근할 수 없어야 한다.
- 최초 FE `START_SESSION`에는 `sessionId`를 넣지 않는다. BE는 자신의 연결 ID를 넣어 AI에 전달한다.
- FE는 `SESSION_STARTED`에서 받은 ID를 이후 요청에 사용한다. BE는 요청 ID와 실제 연결 ID가 다르면 거절한다.
- AI 상태는 `(BE 연결, sessionId)` 단위로 분리한다. 모델 객체는 공유해도 프레임 버퍼, 대상, revision, 마지막 frameIndex, 추론 카운터는 공유하지 않는다.
- AI의 결과·확인 응답·세션 오류는 요청의 `sessionId`를 그대로 반환한다. BE는 소유 FE 한 곳에만 전달한다. 알 수 없거나 종료된 ID의 응답은 폐기한다.
- BE는 AI 공유 연결로 보내는 메시지를 직렬화해 동시 쓰기를 방지한다.

## 2. 공통 필드

| 필드 | 형식 | 의미 |
| --- | --- | --- |
| `protocolVersion` | 정수 `1` | 모든 요청·응답에 필수. 다른 버전은 거절 |
| `type` | 아래 표의 문자열 | 메시지 종류, 대문자 구분 |
| `sessionId` | 비어 있지 않은 문자열 | 최초 FE 시작 요청과 귀속 불가능한 오류를 제외하고 필수 |
| `revision` | 0 이상의 정수 | 세션 내 인식 시도 번호. 시작은 0, 재시도는 현재 값 + 1 |
| `recognitionTarget` | `DEPARTURE` 또는 `ARRIVAL` | 시작·리셋·프레임·결과·시작/리셋 확인에 필수 |
| `timestamp` | 0 이상의 정수 | 송신 시각, Unix epoch milliseconds. 모든 메시지에 필수 |

시각은 진단용이다. 장치 간 시계 차이가 있으므로 메시지 순서는 `revision`, `frameIndex`로 판단한다. 정수는 JavaScript에서 정확히 표현 가능한 범위(최대 9,007,199,254,740,991)로 제한한다.

## 3. 메시지 종류

| 방향 | 요청 | 응답 | 의미 |
| --- | --- | --- | --- |
| FE → BE → AI | `START_SESSION` | `SESSION_STARTED` | 세션 생성 |
| FE → BE → AI | `KEYPOINT_FRAME` | 조건 충족 시 `RESULT` | 프레임 누적·추론. 매 프레임 ACK는 없음 |
| FE → BE → AI | `RESET_SESSION` | `SESSION_RESET` | 해당 세션의 새 인식 시도 |
| FE → BE → AI | `END_SESSION` | `SESSION_ENDED` | 해당 세션 해제 |
| BE 또는 AI → FE | — | `ERROR` | 실패 원인과 요청 종류 전달 |

FE는 `SESSION_STARTED` 또는 `SESSION_RESET`을 받은 뒤 프레임 전송을 시작한다. WebSocket 연결 성공만으로 추론 준비 완료로 표시하지 않는다. BE는 AI 확인을 받기 전에 성공 ACK를 만들지 않는다.

### START_SESSION

최초 FE 요청:

```json
{
  "protocolVersion": 1,
  "type": "START_SESSION",
  "revision": 0,
  "recognitionTarget": "DEPARTURE",
  "timestamp": 1789600000000
}
```

BE가 `sessionId`를 추가해 전달하면 AI는 해당 세션만 만들고 다음 응답을 반환한다.

```json
{
  "protocolVersion": 1,
  "type": "SESSION_STARTED",
  "sessionId": "spring-session-a",
  "revision": 0,
  "recognitionTarget": "DEPARTURE",
  "timestamp": 1789600000001
}
```

이미 활성화된 세션에 대한 START는 `SESSION_ALREADY_STARTED` 오류로 처리한다. 기존 버퍼를 지우지 않는다. 재시도는 RESET으로 요청한다.

### KEYPOINT_FRAME

추가 필드:

| 필드 | 형식 | 검증 |
| --- | --- | --- |
| `frameIndex` | 0 이상의 정수 | revision마다 0부터 시작, 이후 이전 값보다 커야 함. 누락 번호는 허용 |
| `keypoints` | 정확히 137 × 3 배열 | 각 점은 `[x, y, confidence]` |

키포인트 순서는 Pose 25개, Face 70개, 왼손 21개, 오른손 21개다. x/y는 영상 크기 기준 좌표이며 화면 밖 좌표도 유한한 수라면 허용한다. 세 번째 값은 z가 아닌 confidence이고 범위는 0~1이다.

감지되지 않은 점은 `[null, null, 0]`으로 통일한다. x/y 중 하나만 null인 점, NaN/Infinity, 문자열 좌표, 잘못된 크기는 거절한다. confidence가 0인 점은 전처리 시 결측으로 취급한다. 실제 모델 입력의 274차원 벡터는 AI가 생성한다.

다음은 정확한 크기의 요청을 만드는 JavaScript 예시다. 모두 결측인 진단용 프레임이며 실제 수어 예측 예시는 아니다.

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

시작하지 않은 세션은 `SESSION_NOT_FOUND`, 대상 불일치는 `TARGET_MISMATCH`, 오래된 revision은 `STALE_REVISION`, 중복·역순 프레임은 `OUT_OF_ORDER_FRAME`으로 거절한다. 미래 revision은 `INVALID_REVISION`으로 거절하며 RESET 없이 암묵적으로 버퍼를 만들지 않는다. 거절한 입력은 버퍼·인덱스·카운터를 변경하지 않는다.

### RESULT

```json
{
  "protocolVersion": 1,
  "type": "RESULT",
  "sessionId": "spring-session-a",
  "revision": 0,
  "recognitionTarget": "DEPARTURE",
  "timestamp": 1789600005000,
  "frameIndex": 127,
  "departureCity": "서울역",
  "arrivalCity": null,
  "recognizedProb": 98.7
}
```

- `frameIndex`는 추론에 사용한 마지막 프레임의 번호다. 예시의 127은 고정 입력 길이를 의미하지 않는다.
- DEPARTURE이면 `departureCity`만 문자열이고 `arrivalCity`는 null이다. ARRIVAL이면 반대로 반환한다.
- `recognizedProb`는 기존 추론 서비스와 같은 0~100 백분율이다.
- FE는 현재 sessionId·revision·대상이 모두 같은 결과만 표시한다. 이전 frameIndex의 지연 결과가 최신 결과를 덮어쓰지 않아야 한다.
- RESULT는 모델 예측이다. 역 선택 확정은 사용자의 확인 버튼으로 처리한다. `<unk>`는 역으로 확정하지 않고 재시도 상태로 표시한다.
- 시간축 sampling, 버퍼 길이, 추론 간격, 확률 기반 거절 정책은 다음 입력·추론 정책 작업에서 확정한다. 이 규약으로 기존 128/180 정책을 변경하지 않는다.

### RESET_SESSION

```json
{
  "protocolVersion": 1,
  "type": "RESET_SESSION",
  "sessionId": "spring-session-a",
  "revision": 1,
  "recognitionTarget": "ARRIVAL",
  "timestamp": 1789600006000
}
```

FE는 전송을 멈추고 화면 결과를 지운 뒤 현재 revision + 1로 요청한다. AI는 해당 세션의 버퍼·마지막 frameIndex·추론 카운터를 초기화하고 새 대상과 revision을 저장한다. ACK는 요청과 같은 필드에 `type: "SESSION_RESET"`, 응답 시각을 넣어 반환한다.

FE는 ACK 이후 새 revision의 frameIndex 0부터 전송한다. 리셋 이전에 시작된 추론 결과는 AI와 FE 모두 폐기한다. 다른 세션의 상태는 유지한다.

동일 revision·대상의 RESET 재전송은 ACK만 다시 반환하며 버퍼를 다시 비우지 않는다. 현재 revision이 0인 최초 세션에는 이 중복 허용 규칙을 적용하지 않는다. 더 오래된 revision은 `STALE_REVISION`, 건너뛴 revision 또는 같은 revision의 다른 대상은 `INVALID_REVISION`이다.

### END_SESSION

```json
{
  "protocolVersion": 1,
  "type": "END_SESSION",
  "sessionId": "spring-session-a",
  "revision": 1,
  "timestamp": 1789600007000
}
```

현재 revision에 대한 END만 처리한다. AI는 해당 상태를 삭제하고 `SESSION_ENDED`를 같은 ID·revision으로 반환한다. BE는 ACK를 FE에 전달한 뒤 매핑을 삭제한다. 이미 종료된 세션 요청은 `SESSION_NOT_FOUND`로 응답한다. 새로 시작하려면 FE WebSocket을 새로 연결한다.

FE가 ACK 전에 끊어지면 BE가 해당 세션 END를 최선 노력으로 전달하고 매핑을 즉시 정리한다. 공유 AI 연결은 다른 사용자가 쓰므로 닫지 않는다. AI에서 BE 연결이 끊어지면 그 연결 소유의 모든 세션을 제거한다.

## 4. ERROR

```json
{
  "protocolVersion": 1,
  "type": "ERROR",
  "sessionId": "spring-session-a",
  "revision": 1,
  "timestamp": 1789600008000,
  "requestType": "KEYPOINT_FRAME",
  "errorCode": "INVALID_KEYPOINTS",
  "errorMessage": "keypoints must have shape (137, 3)"
}
```

| 코드 | 의미 / 후속 동작 |
| --- | --- |
| `INVALID_JSON` | JSON 파싱 실패. 요청 재구성 |
| `UNSUPPORTED_VERSION` | 지원하지 않는 버전 |
| `UNKNOWN_MESSAGE_TYPE` | 지원하지 않는 type |
| `INVALID_MESSAGE` | 필수 필드 누락·타입·허용값 오류 |
| `SESSION_MISMATCH` | FE 요청 ID가 실제 연결과 다름. 다른 세션에 전달하지 않음 |
| `SESSION_ALREADY_STARTED` | 활성 세션에 START 중복. RESET 사용 |
| `SESSION_NOT_FOUND` | 시작되지 않았거나 종료·만료된 세션. 새 연결에서 START |
| `STALE_REVISION` / `INVALID_REVISION` | 오래되거나 허용되지 않는 인식 시도 번호 |
| `TARGET_MISMATCH` | 세션과 프레임의 인식 대상 불일치. 대상 변경은 RESET |
| `OUT_OF_ORDER_FRAME` | 중복·역순 frameIndex |
| `INVALID_KEYPOINTS` | 크기·좌표·confidence 오류 |
| `MODEL_NOT_READY` | 모델이 준비되지 않아 세션 시작 불가 |
| `INFERENCE_FAILED` | 추론 실패. 오류 표시 후 RESET으로 재시도 |
| `AI_UNAVAILABLE` | BE↔AI 연결 불가·단절. 모든 영향받은 FE에 각각 전달 후 재연결 |
| `SESSION_EXPIRED` | 유휴 만료. 연결을 새로 만들고 START |

BE가 FE의 잘못된 JSON을 처리할 때는 실제 연결 ID로 오류를 돌려준다. AI 공유 연결에서 파싱 실패로 소유 세션을 식별할 수 없는 경우에만 `sessionId`, `revision`, `requestType`에 null을 허용한다. BE는 이 오류를 기록하고 사용자 전체에 방송하지 않는다. 누락된 필드 값은 추측하지 않는다.

오류에 raw 키포인트나 stack trace를 넣지 않는다. 잘못된 한 사용자의 요청 때문에 다른 세션을 삭제하거나 공유 연결을 종료하지 않는다. BE와 AI는 같은 코드를 사용하며 실패를 정상 RESULT로 변환하지 않는다.

## 5. 생명주기와 검증 기준

- 상태 흐름: 연결 → START 대기 → 활성 → RESET 대기 → 활성 → END/연결 종료.
- BE↔AI 연결이 끊어지면 BE는 해당 연결의 세션 매핑을 비우고 각 FE에 `AI_UNAVAILABLE`을 전달한 뒤 FE 연결을 닫는다. 재연결은 새 ID와 revision 0으로 시작한다.
- 유휴 만료 기본값은 120초이며 설정 가능하게 구현한다. 마지막으로 수락한 요청의 서버 단조 시각을 기준으로 측정한다. 손 필터로 프레임 전송이 끊길 수 있으므로 만료를 FE에 명시적으로 알린다.
- AI는 만료 시 `SESSION_EXPIRED`를 보내고 상태를 삭제한다. BE는 소유 FE에 전달하고 매핑과 FE 연결을 정리한다.
- 회귀 검증 대상: A/B 교차 프레임의 버퍼 격리, A 리셋 중 B 유지, 이전 revision 결과 폐기, ID 위조 거절, 대상별 필드 매핑, 잘못된 입력 후 상태 유지, FE 단절·AI 단절·유휴 만료 시 정리.

## 6. 구현 위치와 검증

AI 세션 상태는 `server/realtime/sessions.py`에서 연결별로 관리한다. `ai_server.py`는 모델과 전처리 함수를 연결한다. 수신 루프에서 메시지 처리는 순차 실행되며, 유휴 만료는 1초 간격으로 확인한다(동기 추론 중에는 추론 완료 후 확인). 비동기 worker를 도입할 경우 완료 시 revision 재검증이 추가로 필요하다.

모델 설치 없이 실행 가능한 회귀 테스트: `server` 디렉터리에서 `python -m unittest tests.test_sessions -v`. 실제 ONNX 품질 및 FE↔BE↔AI 통합 테스트는 별도 검증 대상이다.

| 영역 | 현재 구현 |
| --- | --- |
| FE 세션 상태 | recognitionSession.ts에서 ACK·revision·결과 순서 검증 |
| FE 전송 | useKeypointStreaming에서 ACK 제한 시간·재접속·END 관리 |
| BE 요청 | RecognitionMessage로 REST DTO와 분리한 WS envelope 검증 |
| BE 중계 | InferenceClientHandler에서 소유권·라우팅·직렬화·정리 |
| BE 재접속 | AiConnectionConfig에서 기본 5초 간격 재시도 |
| AI 세션 | sessions.py에서 연결 내부 sessionId별 상태 분리 |

회귀 테스트 명령:

- FE: `cd frontend && npm test` (Node.js 22.6+)
- BE: `cd backend && gradle test` (Java 17, Gradle 8.14.4; 현재 저장소에는 wrapper JAR가 없어 별도 Gradle 설치 필요)
- AI: `cd server && python -m unittest tests.test_sessions -v`

BE의 WebSocketRelayIntegrationTest는 실제 로컬 WebSocket과 모의 AI를 사용한다. 이 테스트와 단위 테스트는 실제 카메라·Python 서버·ONNX를 포함한 전체 시스템 검증을 대신하지 않는다. 통합 실행 시 브라우저 두 곳의 출발/도착 인식, 한쪽 RESET 중 다른 쪽 유지, AI 재시작 후 복구를 추가 확인한다.
