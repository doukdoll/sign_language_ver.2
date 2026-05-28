# Frontend API & WebSocket 연동 명세

이 문서는 프론트엔드(`frontend/src/`) 애플리케이션이 백엔드 서버(`http://localhost:8080/api`)와 데이터를 주고받기 위해 사용하는 HTTP REST API 및 WebSocket 통신에 대한 명세입니다.

---

## 1. HTTP REST API (Axios 기반)
주로 사용자의 입력 상태(인원수, 여행 종류, 날짜 등)를 서버에 저장하거나 기차 시간표를 조회할 때 사용됩니다. 관련된 공통 설정과 함수들은 `src/api/axios.ts`에 정의되어 있습니다.

### 1.1. 탑승 인원 설정
- **Endpoint:** `POST /signlanguage/passengers`
- **사용처:** `PassengerPage.tsx`
- **Request Body:**
  ```json
  {
    "signLanguageData": "2", // 사용자가 선택한 인원수 (문자열)
    "recognitionTarget": "passengers"
  }
  ```
- **Description:** 사용자가 선택한 탑승 인원(예: 1~5명)을 서버로 전송합니다.

### 1.2. 여행 종류(편도/왕복) 설정
- **Endpoint:** `POST /signlanguage/triptype`
- **사용처:** `TripTypePage.tsx`
- **Request Body:**
  ```json
  {
    "signLanguageData": "one-way", // 또는 "round"
    "recognitionTarget": "triptype"
  }
  ```
- **Description:** 사용자가 선택한 여정 방식(편도 또는 왕복)을 서버로 전송합니다.

### 1.3. 날짜 및 시간 설정
- **Endpoint:** `POST /signlanguage/datetime`
- **사용처:** `DateTimePage.tsx`
- **Request Body:**
  ```json
  {
    "signLanguageData": "2025-12-18 09:00:00", // 편도의 경우
    // 왕복의 경우: "2025-12-18 09:00:00 | 2025-12-20 18:00:00"
    "recognitionTarget": "datetime"
  }
  ```
- **Description:** 선택한 출발(및 도착) 날짜와 시간을 포맷팅하여 서버로 전송합니다.

### 1.4. 기차 시간표 조회
- **Endpoint:** `GET /train/search`
- **사용처:** `TrainTimeTablePage.tsx`
- **Request Parameters:**
  - `departure`: 출발역 이름 (예: "서울")
  - `destination`: 도착역 이름 (예: "부산")
  - `departureFrom`: 검색 시작 날짜/시간 (예: "2025-12-18 09:00:00")
- **Description:** 설정된 예매 슬롯 데이터를 바탕으로 백엔드(및 DB)에 조건에 맞는 기차 시간표 목록을 조회합니다.

### 1.5. 단발성 수어 인식 (테스트용)
- **Endpoint:** `POST /signlanguage/recognize`
- **사용처:** `useStationRecognition.ts`
- **Request Body:**
  ```json
  {
    "signLanguageData": "{\"gesture\": \"busan\"}", // 가짜 제스처 데이터
    "recognitionTarget": "city"
  }
  ```
- **Description:** 현재는 하드코딩된 제스처 데이터를 보내 단발성 인식을 테스트하는 용도로 사용됩니다.

---

## 2. WebSocket 기반 실시간 스트리밍
웹캠을 통한 사용자의 수어(동작)를 실시간으로 AI 서버가 인식할 수 있도록 백엔드와 양방향 통신을 수행합니다. 관련 로직은 `src/hooks/useKeypointStreaming.ts`에서 관리합니다.

- **WebSocket URL:** `ws://localhost:8080/api/sign/stream`
- **사용처:** `DeparturePage.tsx` (출발역 선택), `ArrivalPage.tsx` (도착역 선택)

### 2.1. 세션 시작 (Frontend ➔ Backend)
연결이 수립된 직후, 어떤 데이터를 인식할 것인지 서버에 알립니다.
```json
{
  "type": "START_SESSION",
  "sessionId": "session-17109283-abc123xyz",
  "timestamp": 1710928392019,
  "recognitionTarget": "DEPARTURE" // 또는 "ARRIVAL"
}
```

### 2.2. 실시간 키포인트 프레임 전송 (Frontend ➔ Backend)
MediaPipe에서 추출한 137개의 관절 좌표(정규화된 배열)를 목표 FPS(예: 30)에 맞춰 지속적으로 스트리밍합니다.
```json
{
  "type": "KEYPOINT_FRAME",
  "sessionId": "session-17109283-abc123xyz",
  "timestamp": 1710928392500,
  "frameIndex": 45,
  "keypoints": [
    [0.45, 0.23, 0.98], // [x, y, confidence] 형태가 137개
    // ...
  ],
  "recognitionTarget": "DEPARTURE"
}
```

### 2.3. 인식 결과 수신 (Backend ➔ Frontend)
서버(AI 모듈 연동)에서 특정 단어를 성공적으로 인식하면 결과를 프론트엔드로 푸시합니다. 프론트엔드는 이 데이터를 받아 UI(`RecognitionResult` 컴포넌트 등)에 즉시 표시합니다.
```json
{
  "departureCity": "서울역", // recognitionTarget이 DEPARTURE일 때
  "arrivalCity": null,
  "recognizedProb": 0.95
}
```
*(참고: 서버 구현에 따라 `type: "RESULT"`, `label: "서울역"` 등의 형태로 응답이 오기도 하며 프론트엔드에서 Fallback으로 처리합니다.)*
