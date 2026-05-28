# Backend API 연동 명세 (Spring Boot)

이 문서는 프론트엔드에서 호출하는 백엔드(`http://localhost:8080/api`)의 주요 REST API 엔드포인트와 웹소켓(WebSocket) 설정에 대한 명세입니다. 해당 명세는 Java Spring Boot 컨트롤러 및 핸들러 코드를 기반으로 작성되었습니다.

---

## 1. REST API Endpoints

### 1.1. 헬스 체크
- **URL:** `GET /health/ping`
- **Controller:** `HealthController`
- **Description:** 서버의 정상 작동 여부를 확인합니다.
- **Response:** `pong` (String)

### 1.2. 수어 인식 관련 (Sign Language)
- **Base URL:** `/signlanguage`
- **Controller:** `SignLanguageController`
- **Description:** 프론트엔드에서 사용자의 수어 입력을 전달받아 해석하는 역할을 합니다. (현재 코드는 내부 서비스나 AI 모델 연동의 테스트용도로 주로 사용됩니다.)

#### 1) 도시(역) 인식
- **URL:** `POST /signlanguage/recognize`
- **Request Body:** `SignLanguageInputDto` (주로 `signLanguageData`, `recognitionTarget` 필드)
- **Response:** `CityRecognitionResponseDto` (예: `{"departureCity": "서울", "arrivalCity": null}`)

#### 2) 날짜 및 시간 인식
- **URL:** `POST /signlanguage/datetime`
- **Request Body:** `SignLanguageInputDto`
- **Response:** `DateTimeRecognitionResponseDto` (예: `{"recognizedDate": "2025-11-05", "recognizedTime": "14:30"}`)

#### 3) 승객 수 인식
- **URL:** `POST /signlanguage/passengers`
- **Request Body:** `SignLanguageInputDto`
- **Response:** `PassengerRecognitionResponseDto` (예: `{"recognizedPassengers": 2}`)

#### 4) 여행 종류(편도/왕복) 인식
- **URL:** `POST /signlanguage/triptype`
- **Request Body:** `SignLanguageInputDto`
- **Response:** `TripTypeRecognitionResponseDto` (예: `{"recognizedTripType": "왕복"}`)

#### 5) 좌석 등급 인식
- **URL:** `POST /signlanguage/seatclass`
- **Request Body:** `SignLanguageInputDto`
- **Response:** `SeatClassRecognitionResponseDto` (예: `{"recognizedSeatClass": "일반실"}`)

### 1.3. 기차 시간표 조회 (Train)
- **URL:** `GET /train/search`
- **Controller:** `TrainController`
- **Request Parameters:**
  - `departure` (String, Optional): 출발역
  - `destination` (String, Optional): 도착역
  - `departureFrom` (LocalDateTime, Optional): 검색 시작 시간 (Format: `yyyy-MM-dd HH:mm`)
  - `departureTo` (LocalDateTime, Optional): 검색 종료 시간 (Format: `yyyy-MM-dd HH:mm`)
- **Response:** `List<TrainInfoDto>` (조건에 맞는 기차 시간표 리스트 반환, 내부적으로 CSV 데이터 기반 `TrainScheduleRepository` 이용)

### 1.4. 예매 (Booking)
- **URL:** `POST /booking/train`
- **Controller:** `BookingController`
- **Request Body:** `BookingRequestDto` (열차 번호, 출발/도착역, 출발/도착 시간, 승객 수, 좌석 종류, 결제 수단 등 포함)
- **Response:** `TicketDto` (HTTP 201 CREATED) - 생성된 예약 번호(Booking ID), 결제 금액, QR 코드 데이터 등을 반환합니다.

### 1.5. 결제 (Payment)
- **URL:** `/payment/**`
- **Controller:** `PaymentController`
- **Description:** 현재 뼈대만 잡혀 있으며, 구체적인 API 구현은 `TODO` 상태입니다.

---

## 2. WebSocket 연동 (실시간 수어 인식)

### 2.1. 프론트엔드 연동용 (FE ↔ BE)
- **URL:** `ws://localhost:8080/sign/stream` (또는 `/api/sign/stream`)
- **Handler:** `PredictionClientHandler`
- **기능:**
  - 프론트엔드로부터 `START_SESSION`, `KEYPOINT_FRAME` 등 타입의 메시지를 `SignLanguageInputDto` 형태로 파싱하여 받습니다.
  - 들어온 키포인트 데이터를 AI 서버 전용 세션(`InferenceClientHandler`)을 통해 파이썬 서버로 포워딩합니다.
  - 파이썬 서버에서 보낸 결과(`CityRecognitionResponseDto` 등)를 받아 다시 프론트엔드로 전달합니다.

### 2.2. AI 모델 서버 연동용 (BE ↔ Python AI)
- **URL:** `ws://localhost:5001/ws/predict` (Flask 서버 주소)
- **Handler:** `InferenceClientHandler` (Spring 클라이언트 역할 수행, `AiConnectionConfig`에서 설정)
- **기능:**
  - 스프링 부트 서버 기동 시 자동으로 파이썬 AI 서버로 WebSocket 연결을 시도합니다.
  - 프론트엔드에서 수신된 키포인트 데이터를 AI 서버에 포워딩(`sendToAI`)합니다.
  - AI 서버의 추론 결과 JSON을 받아 `Session ID`를 기준으로 매핑된 프론트엔드 클라이언트(`PredictionClientHandler`)에게 반환합니다.
