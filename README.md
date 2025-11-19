# Sign Language Transport Backend

농인을 위한 수어 기반 대중교통 플랫폼 백엔드 서비스

## 기술 스택

### 백엔드
- Java 17
- Spring Boot 3.2.5
- Spring Data JPA
- Spring WebFlux (비동기 HTTP 클라이언트)
- Spring Security
- H2 Database (개발용) / MySQL (운영용)
- ZXing (QR코드 생성)
- Jackson (JSON 처리)
- OpenCSV (CSV 파일 파싱)
- SpringDoc OpenAPI (Swagger UI)

### AI 모델
- MediaPipe (키포인트 추출)
- GRU 기반 수어 인식 모델
- 실시간 추론 시스템

## 프로젝트 구조

```
src/main/java/com/capstone/
├── SignLanguageTransportApplication.java    # 메인 애플리케이션
├── config/                                 # 설정 클래스
│   ├── WebConfig.java
│   └── SecurityConfig.java
├── controller/                             # REST API 컨트롤러
│   ├── HealthController.java               # 헬스 체크 엔드포인트
│   ├── TrainController.java
│   ├── BookingController.java
│   ├── PaymentController.java
│   └── SignLanguageController.java         # 수어 인식 컨트롤러
├── service/                                # 비즈니스 로직
│   ├── KorailService.java
│   ├── TrainDataLoader.java                # CSV 데이터 로딩
│   ├── BookingService.java
│   ├── PaymentService.java
│   └── SignLanguageService.java            # 수어 인식 서비스
├── entity/                                 # JPA 엔티티
│   ├── TrainSchedule.java                  # 열차 시간표 엔티티
│   ├── Booking.java
│   └── Payment.java
├── dto/                                     # 데이터 전송 객체
│   ├── SlotDataDto.java
│   ├── TrainInfoDto.java
│   ├── BookingRequestDto.java
│   ├── SignLanguageInputDto.java
│   ├── CityRecognitionResponseDto.java
│   ├── DateTimeRecognitionResponseDto.java
│   ├── PassengerRecognitionResponseDto.java
│   ├── TripTypeRecognitionResponseDto.java
│   └── SeatClassRecognitionResponseDto.java
├── repository/                              # 데이터 접근 계층
│   ├── TrainScheduleRepository.java        # 열차 시간표 리포지토리
│   ├── BookingRepository.java
│   └── PaymentRepository.java
└── util/                                    # 유틸리티
    ├── JsonParser.java
    └── QrGenerator.java

```

## 주요 기능

### 백엔드 실행
```bash
cd backend
./gradlew clean build --refresh-dependencies
./gradlew bootRun
```

### 1. 기차 조회 (Train)
- 출발지, 목적지, 출발 시간 등 조건에 따른 열차 시간표 검색
- CSV 파일을 통한 열차 시간표 데이터베이스 적재
- AI에서 받은 슬롯 데이터로 기차 검색 (향후 개발 예정)

### 2. 예매 (Booking)
- 기차 예매 생성
- 예매 조회 및 취소
- 예매 번호 생성

### 3. 결제 (Payment)
- 결제 처리 및 상태 관리
- 환불 처리
- 결제 시뮬레이션

### 4. 유틸리티
- JSON 파싱 (AI 슬롯 데이터)
- QR코드 생성 (예매 완료 후)

## API 엔드포인트

### 헬스 체크
- `GET /api/health/ping` - 서버 상태 확인 (응답: `pong`)

### 기차 조회
- `GET /api/train/search` - 열차 시간표 검색
  - **Request Parameters:**
    - `departure` (Optional): 출발역 이름 (예: `서울`)
    - `destination` (Optional): 도착역 이름 (예: `부산`)
    - `departureFrom` (Optional): 검색 시작 시간 (ISO 8601 형식: `YYYY-MM-DDTHH:MM:SS`, 예: `2025-10-15T10:00:00`). 미입력 시 현재 시간부터 검색됩니다.
    - `departureTo` (Optional): 검색 종료 시간 (ISO 8601 형식: `YYYY-MM-DDTHH:MM:SS`, 예: `2025-10-15T18:00:00`)
  - **응답**: 조건에 맞는 열차 시간표 목록 (출발 시간 기준 오름차순 정렬)
- `POST /api/train/search` - 슬롯 데이터로 기차 검색 (향후 AI 연동 시 사용)
- `GET /api/train/{trainNumber}` - 특정 기차 정보 조회

### 예매
- `POST /api/booking` - 예매 생성
- `GET /api/booking/{bookingNumber}` - 예매 조회
- `GET /api/booking` - 전체 예매 조회
- `PUT /api/booking/{bookingNumber}/cancel` - 예매 취소

### 결제
- `POST /api/payment/{bookingId}` - 결제 처리
- `GET /api/payment/{paymentId}` - 결제 조회
- `GET /api/payment/booking/{bookingId}` - 예매별 결제 조회
- `POST /api/payment/{paymentId}/refund` - 환불 처리

## 실행 방법

### 1. 개발 환경 준비

-   **Java Development Kit (JDK) 17 이상** 설치
-   **Gradle** 설치 (또는 `./gradlew` Wrapper 사용)

### 2. 프로젝트 빌드 및 실행

1.  **프로젝트 클론**
    ```bash
    git clone [프로젝트_레포지토리_주소]
    cd SignLanguageTransport/backend
    ```
2.  **의존성 설치 및 빌드 (Gradle)**
    ```bash
    ./gradlew clean build --refresh-dependencies
    ```
    *   `--refresh-dependencies`: Gradle 캐시 문제를 해결하기 위해 필요할 수 있습니다.
3.  **애플리케이션 실행 (Gradle)**
    ```bash
    ./gradlew bootRun
    ```
    *   애플리케이션이 시작되면, `src/main/resources` 디렉토리에 있는 `경부선하행.csv`와 `경부선상행.csv` 파일의 데이터가 H2 인메모리 데이터베이스에 자동으로 적재됩니다. (이 과정에서 잠시 시간이 소요될 수 있습니다.)

### 3. 애플리케이션 확인

-   **H2 콘솔**: `http://localhost:8080/api/h2-console`
    *   JDBC URL: `jdbc:h2:mem:testdb`
    *   User Name: `sa`
    *   Password: `(비워둠)`
    *   `Connect` 버튼을 클릭하여 데이터베이스를 탐색할 수 있습니다. `TRAIN_SCHEDULE` 테이블에서 CSV 데이터가 잘 적재되었는지 확인해 보세요.
-   **API Base URL**: `http://localhost:8080/api`
-   **헬스 체크**: `http://localhost:8080/api/health/ping` (브라우저에서 접속 시 `pong` 응답 확인)
-   **Swagger UI**: `http://localhost:8080/api/swagger-ui/index.html`
    *   API 문서와 테스트를 위해 이 주소로 접속하세요. `GET /api/train/search` 엔드포인트를 통해 열차 시간표 조회 기능을 테스트할 수 있습니다.

## 환경 설정

### 개발 환경 (application-dev.yml)
- H2 인메모리 데이터베이스
- SQL 로깅 활성화
- 디버그 로그 활성화
- CSV 데이터는 애플리케이션 시작 시 H2 데이터베이스에 자동으로 적재됩니다.

### 운영 환경 (application-prod.yml)
- MySQL 데이터베이스
- 로그 레벨 최적화
- 보안 설정 강화

## 향후 개발 계획

1. **코레일 API 실제 연동**
2. **카카오톡 API 연동** (예매 정보 전송)
3. **지하철 API 연동**
4. **실제 결제 시스템 연동**
5. **보안 강화** (JWT 토큰, 암호화)
6. **모니터링 및 로깅** (Actuator, Logback)

