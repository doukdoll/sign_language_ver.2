# Backend

기차 시간표 조회와 예매 생성을 제공하고, 프론트엔드의 키포인트 스트림을 Python AI 서버로 중계하는 Spring Boot 애플리케이션입니다.

## 기술 스택

- Java 17
- Spring Boot 3.2.5
- Spring MVC, Validation, Security
- Spring WebSocket
- Spring Data JPA
- H2 개발 DB, MySQL 운영 DB
- OpenCSV, ZXing, Lombok
- SpringDoc OpenAPI 2.5.0

## 구현 범위

| 영역 | 상태 | 설명 |
| --- | --- | --- |
| 열차 데이터 초기화 | 구현 | 경부선 상·하행 CSV를 읽어 오늘부터 한 달 뒤까지의 운행 데이터를 생성합니다. |
| 열차 검색 | 구현 | 출발역, 도착역, 출발 시간 조건으로 H2/MySQL을 조회합니다. |
| 예매 생성 | 구현 | 열차 스케줄을 확인하고 예매 정보와 QR용 문자열을 저장합니다. |
| 실시간 수어 중계 | 구현 | WebSocket 규약 v1에 따라 세션 소유권·ACK·revision을 검증하고 AI 응답을 소유 FE에만 전달합니다. |
| 수어 REST API | 임시 구현 | 도시·날짜·인원·여정·좌석 등급 응답은 현재 고정값입니다. |
| 결제 API | 미구현 | 컨트롤러와 서비스만 있고 엔드포인트는 없습니다. |
| 인증·인가 | 미구현 | 현재 주요 API와 WebSocket은 인증 없이 접근할 수 있습니다. |

## 실행

### 요구 사항

- JDK 17
- Gradle 8.14.4 별도 설치 및 PATH 설정 (현재 저장소에 `gradle-wrapper.jar`가 없어 `gradlew`는 실행할 수 없습니다.)
- AI 연동을 확인하려면 `ws://localhost:5001/ws/predict`에서 실행 중인 추론 서버

저장소 루트에서 실행합니다. Windows PowerShell과 macOS/Linux에서 같은 명령을 사용합니다.

```bash
cd backend
gradle bootRun
```

기본 프로필은 `dev`이며 H2 인메모리 DB를 사용합니다. 애플리케이션이 시작되면 두 CSV 파일을 읽어 열차 스케줄을 자동 생성합니다.

AI 중계만 확인하려면 `gradle bootRun --args="--spring.profiles.active=test"`로 CSV 적재를 생략할 수 있습니다. 이 경우 열차 조회용 초기 데이터는 생성되지 않습니다.

## 접속 주소

| 용도 | 주소 |
| --- | --- |
| API base URL | `http://localhost:8080/api` |
| Health check | `http://localhost:8080/api/health/ping` |
| Swagger UI | `http://localhost:8080/api/swagger-ui.html` |
| OpenAPI JSON | `http://localhost:8080/api/v3/api-docs` |
| H2 Console | `http://localhost:8080/api/h2-console` |
| Frontend WebSocket | `ws://localhost:8080/api/sign/stream` |

H2 Console 기본값:

```text
JDBC URL: jdbc:h2:mem:testdb
User Name: sa
Password: (빈 값)
```

## HTTP API

모든 경로 앞에는 context path `/api`가 붙습니다.

### 상태 확인

```http
GET /api/health/ping
```

응답:

```text
pong
```

### 열차 검색

```http
GET /api/train/search
```

| Query parameter | 필수 | 형식 | 설명 |
| --- | --- | --- | --- |
| `departure` | 아니요 | 문자열 | 출발역입니다. |
| `destination` | 아니요 | 문자열 | 도착역입니다. |
| `departureFrom` | 아니요 | `yyyy-MM-dd HH:mm` | 생략하면 현재 시각을 사용합니다. |
| `departureTo` | 아니요 | `yyyy-MM-dd HH:mm` | 조회 결과의 마지막 출발 시각입니다. |

예시:

```text
GET /api/train/search?departure=서울&destination=부산&departureFrom=2026-09-17%2009:00
```

검색 범위는 `departureFrom`이 속한 날짜의 다음 날 00:00 이전까지입니다. 응답의 좌석 수, 좌석 등급, 가격, 상태는 현재 임시값으로 생성됩니다.

출발역과 도착역을 모두 지정한 경우 한쪽의 `대구`를 동대구·서대구로 확장합니다. 도착역 조건을 먼저 처리하므로 양쪽 모두 `대구`인 경우나 역 조건을 하나만 보낸 경우에는 일반적인 별칭 정규화가 적용되지 않습니다.

### 예매 생성

```http
POST /api/booking/train
Content-Type: application/json
```

요청 예시:

```json
{
  "trainNumber": "KTX101",
  "departureStation": "서울",
  "arrivalStation": "부산",
  "departureTime": "2026-09-17T09:00:00",
  "arrivalTime": "2026-09-17T11:30:00",
  "passengers": 1,
  "seatType": "STANDARD",
  "paymentMethod": "card",
  "tripType": "one_way"
}
```

`trainNumber`, `departureTime`, `arrivalTime`이 DB의 스케줄과 정확히 일치해야 합니다. 좌석 번호는 현재 `12호차 34A석`으로 고정되며 실제 좌석 재고를 차감하지 않습니다.

### 수어 입력용 REST API

```text
POST /api/signlanguage/recognize
POST /api/signlanguage/datetime
POST /api/signlanguage/passengers
POST /api/signlanguage/triptype
POST /api/signlanguage/seatclass
```

공통 요청 형태:

```json
{
  "signLanguageData": "입력값",
  "recognitionTarget": "DEPARTURE"
}
```

이 엔드포인트들은 현재 실제 모델을 호출하지 않습니다. `recognize`는 출발지 `서울` 또는 도착지 `부산`, 나머지는 날짜 `2025-11-05 14:30`, 승객 `2`, 여정 `왕복`, 좌석 `일반실` 같은 고정 응답을 반환합니다.

## WebSocket 중계

현재 중계는 [WebSocket 규약 v1](../docs/RECOGNITION_PROTOCOL.md)을 사용합니다.

- FE 연결: ws://localhost:8080/api/sign/stream
- AI 연결: ws://localhost:5001/ws/predict
- 최초 START에 BE WebSocket ID를 추가하고, 이후에는 FE 요청 ID가 실제 연결 ID와 같은지 검사합니다.
- ACK/RESULT/ERROR는 WS 전용 RecognitionMessage 검증 및 JSON 트리로 처리합니다. 기존 REST DTO는 변경하지 않습니다.
- AI 응답을 ID 소유자에게만 전달하고 START/RESET ACK 전에는 프레임을 받지 않습니다. 공유 AI 소켓 쓰기는 직렬화합니다.
- FE 종료 시 해당 세션 END만 전달합니다. AI 단절 시 영향받는 FE에 AI_UNAVAILABLE을 알리고 매핑과 연결을 정리합니다.
- AI 연결을 기본 5초 간격으로 재시도합니다. 재접속 중인 연결 시도는 중복 생성하지 않습니다. 복구 후 기존 버퍼를 복원하지 않고 FE가 새 세션으로 시작합니다.
- 유휴 만료는 AI가 판정하며 SESSION_EXPIRED를 받은 FE만 정리합니다.

## 설정

주요 Spring property와 환경변수 이름은 다음과 같습니다.

| Property | 설정 방법 또는 사용 환경변수 | 기본값 |
| --- | --- | --- |
| `ai-server.ws-url` | `AI-SERVER_WS-URL` | `ws://localhost:5001/ws/predict` |
| `ai-server.http-url` | `AI-SERVER_HTTP-URL` | `http://localhost:5001/predict_keypoints` |
| `ai-server.reconnect-delay-ms` | Spring 실행 인자 또는 설정 파일 | `5000` |
| `spring.profiles.active` | Spring 실행 인자 또는 `SPRING_PROFILES_ACTIVE` | `dev` |
| 운영 DB 사용자 | `DB_USERNAME` | `root` |
| 운영 DB 비밀번호 | `DB_PASSWORD` | `password` |

직접 실행하면서 AI 주소를 바꾸려면 Spring property `ai-server.ws-url`, `ai-server.http-url`을 JVM 옵션이나 별도 설정 파일로 전달할 수 있습니다.

AI 주소 환경변수 표기는 현재 `docker-compose.yml`에 적힌 값입니다. Compose 전체 실행의 제한 사항은 [루트 README](../README.md)를 확인하세요.

`prod` 프로필은 `jdbc:mysql://localhost:3306/sign_language_transport`에 접속하고 Hibernate `validate` 모드를 사용합니다. 스키마는 자동 생성되지 않습니다.

## 프로젝트 구조

```text
src/main/java/com/capstone/
├── config/         # CORS, Security, WebSocket, 예외 처리
├── controller/     # REST 컨트롤러
├── dto/            # 요청·응답 객체
├── entity/         # Booking, Payment, TrainSchedule
├── handler/        # Frontend/AI WebSocket 핸들러
├── repository/     # JPA repository
├── service/        # 열차, 예매, 수어, 데이터 적재 로직
└── util/           # JSON, QR 문자열 유틸리티
```

## 테스트와 빌드

`backend` 디렉터리에서 실행합니다.

```bash
gradle test
gradle --no-daemon --console=plain clean build
```

현재 테스트는 16개입니다. `InferenceClientHandlerTest` 12개는 ID 위조, 응답 라우팅, RESET, 연결 종료/만료, 동시 쓰기를 검사합니다.

`WebSocketRelayIntegrationTest` 1개는 임의 로컬 포트에서 실제 FE WebSocket 두 개와 공유 AI 연결을 열어 중계를 검증합니다. AI는 결정적 응답을 반환하는 모의 서버이며 모델 추론을 수행하지 않습니다. `SignLanguageServiceIntegrateTest` 3개는 MockRestServiceServer로 기존 HTTP 서비스의 요청 형식과 오류 응답을 검사합니다.

[GitHub Actions CI](../.github/workflows/ci.yml)는 `develop` 대상 PR과 `develop` push에서 Java 17·Gradle 8.14.4로 `clean build`를 실행합니다. 테스트 보고서는 `backend-test-reports` 아티팩트로 최대 7일 보관합니다. 실제 Python·ONNX·카메라 검증은 CI와 별개이며 [실시간 연동 검증 문서](../docs/LIVE_RECOGNITION_CHECK.md)를 참고하세요.

## 현재 제한 사항

- `PaymentController`와 `PaymentService`에는 구현된 API가 없습니다.
- `recognizeCity_with_AI` HTTP 연동 메서드는 존재하지만 현재 REST 컨트롤러에서 호출하지 않습니다.
- AI WebSocket 응답에 `sessionId`가 없으면 프론트로 결과를 전달할 수 없습니다.
- AI 연결 재시도 간격은 `ai-server.reconnect-delay-ms`(기본 5000)로 설정합니다. 실패 중에는 정상 인식 결과를 반환하지 않습니다.
- CORS와 주요 API가 전체 허용 상태이므로 운영 환경에 그대로 사용하면 안 됩니다.
- 좌석, 요금, 결제는 실제 외부 시스템과 연동되지 않은 프로토타입 값입니다.
