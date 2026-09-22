# Backend API 연동 명세

현재 Spring Boot 컨트롤러·서비스·WebSocket 핸들러 기준입니다. 기본 HTTP 주소는 `http://localhost:8080/api`이며 아래 상대 경로에는 모두 context path `/api`가 붙습니다. 실행·설정·검증 명령은 [Backend README](backend/README.md), WebSocket의 전체 계약은 [실시간 인식 규약 v1](docs/RECOGNITION_PROTOCOL.md)을 참고하세요.

## 1. REST API

### 상태 확인

- `GET /health/ping`
- `HealthController`가 문자열 `pong`을 반환합니다.

### 수어 입력용 임시 API

`SignLanguageController`는 다음 API를 제공합니다. 현재 컨트롤러가 호출하는 서비스는 **모델을 실행하지 않고 고정값을 반환**합니다. 입력 선택값을 DB에 저장하는 API도 아닙니다.

| 상대 경로 | 응답 DTO | 현재 응답 |
| --- | --- | --- |
| `POST /signlanguage/recognize` | `CityRecognitionResponseDto` | 대상이 `DEPARTURE`이면 `departureCity: "서울"`, `ARRIVAL`이면 `arrivalCity: "부산"`; 반대쪽 필드는 null |
| `POST /signlanguage/datetime` | `DateTimeRecognitionResponseDto` | `recognizedDate: "2025-11-05"`, `recognizedTime: "14:30"` |
| `POST /signlanguage/passengers` | `PassengerRecognitionResponseDto` | `recognizedPassengers: 2` |
| `POST /signlanguage/triptype` | `TripTypeRecognitionResponseDto` | `recognizedTripType: "왕복"` |
| `POST /signlanguage/seatclass` | `SeatClassRecognitionResponseDto` | `recognizedSeatClass: "일반실"` |

공통 요청은 `SignLanguageInputDto`를 사용합니다.

```json
{
  "signLanguageData": "입력값",
  "recognitionTarget": "DEPARTURE"
}
```

`recognize`에 `DEPARTURE`/`ARRIVAL` 이외 대상을 보내면 현재 서비스는 두 역 필드에 각각 `알 수 없는 출발지`, `알 수 없는 도착지`를 반환합니다. `recognizeCity_with_AI` HTTP 서비스 메서드는 별도로 존재하지만 이 컨트롤러에서는 호출하지 않습니다. 실제 출발역·도착역 AI 인식은 아래 WebSocket 경로를 사용합니다.

### 열차 시간표 조회

- `GET /train/search`
- `TrainController` → `KorailService` → `TrainScheduleRepository`
- 응답: `List<TrainInfoDto>`

| Query parameter | 필수 | 형식·동작 |
| --- | --- | --- |
| `departure` | 아니요 | 출발역 문자열 |
| `destination` | 아니요 | 도착역 문자열 |
| `departureFrom` | 아니요 | `yyyy-MM-dd HH:mm`; 생략하면 현재 시각 |
| `departureTo` | 아니요 | `yyyy-MM-dd HH:mm`; 결과의 출발 시각에 추가 상한 적용 |

기본 조회 범위는 `departureFrom` 이상, 그 날짜의 다음 날 00:00 미만입니다. 데이터는 저장소의 CSV에서 생성한 DB 스케줄이며 외부 철도 운영 API의 실시간 조회가 아닙니다. 두 역 조건이 모두 있을 때 한쪽의 `대구`를 동대구·서대구로 확장하는 분기가 있습니다(도착역 우선). 모든 조건에 적용되는 공통 별칭 정규화는 아닙니다.

응답의 `seatType`은 `STANDARD`, `availableSeats`는 50, `price`는 50000, `status`는 `available`로 고정됩니다. 이 값으로 실제 좌석 재고나 요금을 판단하면 안 됩니다.

### 예매 생성

- `POST /booking/train`
- `BookingController` → `BookingService`
- 요청: `BookingRequestDto`
- 성공 응답: HTTP 201, `TicketDto`

```json
{
  "trainNumber": "101",
  "departureStation": "서울",
  "arrivalStation": "부산",
  "departureTime": "2026-09-22T09:00:00",
  "arrivalTime": "2026-09-22T11:30:00",
  "passengers": 1,
  "seatType": "STANDARD",
  "paymentMethod": "card",
  "tripType": "one_way"
}
```

위 값은 형식 예시이며 실행 시 DB에 존재하는 열차 번호·출발 시각·도착 시각으로 바꿔야 합니다. 승객 수는 1~9명입니다. 예약 ID와 QR용 문자열을 생성하여 저장하고, 좌석은 `12호차 34A석`으로 고정합니다. 반환 금액은 DB 스케줄 가격 × 승객 수이며 검색 응답의 고정 가격과는 다를 수 있습니다. 실제 결제 승인이나 좌석 재고 차감은 없습니다. 현재 FE 예매 흐름에서도 이 API를 호출하지 않습니다.

### 결제

`PaymentController`에 `/payment` 클래스 매핑은 있지만 메서드 엔드포인트는 없습니다. 호출 가능한 결제 API로 문서화하지 않습니다.

## 2. WebSocket v1

### 연결 주소와 책임

| 구간 | 기본 주소 | 담당 |
| --- | --- | --- |
| FE ↔ BE | `ws://localhost:8080/api/sign/stream` | `PredictionClientHandler`가 FE 메시지와 연결 생명주기를 중계 관리자에게 전달 |
| BE ↔ AI | `ws://localhost:5001/ws/predict` | `InferenceClientHandler`가 공유 AI 연결, 세션 소유권, 응답 라우팅 관리 |

BE 연결 주소는 `ai-server.ws-url`로 변경합니다. `AiConnectionConfig`가 기본 5초 간격으로 연결을 시도하며, 진행 중인 연결 시도는 중복 생성하지 않습니다.

### 메시지 처리

- WS 전용 `RecognitionMessage`와 JSON 트리를 사용합니다. REST의 `SignLanguageInputDto`/`CityRecognitionResponseDto`로 파싱하는 경로가 아닙니다.
- 최초 FE `START_SESSION`은 `sessionId` 없이 `protocolVersion: 1`, `revision: 0`, `recognitionTarget`, `timestamp`를 전송합니다. BE가 실제 FE WebSocket ID를 추가합니다.
- FE는 AI의 `SESSION_STARTED`에서 받은 ID를 이후 요청에 사용합니다. BE는 ID 위조를 거절하고 START/RESET ACK 이전 프레임을 전달하지 않습니다.
- `KEYPOINT_FRAME`은 정확히 137 × 3 키포인트와 `frameIndex`를 포함합니다. `RESET_SESSION`은 revision을 1 증가시키고 `SESSION_RESET` 이후 프레임 번호 0부터 재개합니다.
- AI 응답의 ID·revision·대상을 검증하여 소유 FE 한 곳에만 전달합니다. `RESULT.recognizedProb`는 **0~100 백분율**입니다.
- FE 종료 시 그 세션의 `END_SESSION`만 최선 노력으로 전달하며 공유 AI 연결은 유지합니다.
- AI 단절은 영향받는 FE에 `AI_UNAVAILABLE`을 알린 뒤 연결·매핑을 정리합니다. 재연결하면 새 ID와 revision 0으로 시작합니다. 유휴 만료는 AI가 `SESSION_EXPIRED`로 알립니다.

필수 필드, JSON 예시, 오류 코드, 중복 RESET 및 프레임 순서 규칙은 [공통 규약](docs/RECOGNITION_PROTOCOL.md)을 기준으로 합니다. 인증·인가와 운영용 CORS 제한은 아직 적용되지 않았습니다.

## 3. 검증 범위

현재 BE 테스트 16개는 중계 회귀 12개, 실제 로컬 WebSocket + 모의 AI 통합 1개, 모의 HTTP 서비스 테스트 3개입니다. [CI](.github/workflows/ci.yml)는 `develop` 대상 PR과 push에서 Java 17·Gradle 8.14.4로 빌드와 테스트를 실행합니다.

모의 AI 테스트는 실제 모델 품질을 검증하지 않습니다. 실제 Python·ONNX 연동 스모크와 브라우저 확인은 [별도 검증 문서](docs/LIVE_RECOGNITION_CHECK.md)에 구분합니다.
