# Sign Language Transport Platform (농인을 위한 수어 기반 대중교통 예매 키오스크)

본 프로젝트는 청각장애인(농인)이 기차역 키오스크나 모바일 환경에서 수어를 통해 대중교통(기차)을 원활하게 예매할 수 있도록 돕는 **수어 인식 기반 예매 플랫폼**입니다. 사용자의 수어 동작을 실시간으로 인식하여 출발지, 도착지, 날짜, 인원수 등을 파악하고 실제 예매 및 결제까지 이어지도록 설계되었습니다.

전체 시스템은 **프론트엔드(키오스크 UI)**, **백엔드(예매 및 비즈니스 로직)**, **AI 서버(실시간 수어 인식 및 번역)** 세 가지 주요 모듈로 구성되어 있습니다.

---

## 🛠 기술 스택 (Tech Stack)

### Frontend (Kiosk)
- **Framework:** React 19, TypeScript, Vite
- **Styling:** Tailwind CSS, PostCSS
- **Camera & AI:** MediaPipe (Holistic), react-webcam
- **Routing & HTTP:** React Router DOM, Axios

### Backend (Core API)
- **Framework:** Java 17, Spring Boot 3.2.5
- **Data & DB:** Spring Data JPA, H2 (개발용), MySQL (운영용)
- **Network & Security:** Spring WebFlux, Spring Security
- **Docs & Utils:** SpringDoc OpenAPI (Swagger), OpenCSV, ZXing (QR)

### AI Server (Sign Language Translation)
- **Language & Framework:** Python 3.9+, PyTorch 2.0+, FastAPI (또는 Flask)
- **AI Models:** MediaPipe, GRU / Transformer (Attention, Beam Search 지원)
- **Data Pipeline:** OpenPose 정규화(BODY_25, Face70, Hands) 기반 데이터 전처리 프로세서

---

## 📁 프로젝트 구조 (Project Structure)

```text
C:\sign_language_ver.2\
├── backend/            # Spring Boot REST API 서버 (예매, 결제, 기차 데이터 관리)
├── frontend/           # React + Vite 기반 사용자 인터페이스 (웹캠 캡처, 키오스크 화면)
└── server/             # Python 기반 실시간 수어 인식 및 번역 AI 서버 (KSLT)
```

---

## ✨ 주요 기능 (Key Features)

1. **실시간 수어 인식 및 예매 정보 추출 (Frontend + AI Server)**
   - 프론트엔드에서 웹캠을 통해 사용자의 수어 동작 캡처 및 MediaPipe 랜드마크 추출
   - AI 서버에서 랜드마크 데이터를 정규화하고 GRU/Transformer 모델을 통해 '서울역', '내일', '어른 두 명' 등의 단어로 실시간 번역
   - 검증된 단어들을 조합하여 예매 슬롯(출발지, 도착지, 날짜, 인원 등) 완성
2. **기차 시간표 조회 및 데이터베이스 적재 (Backend)**
   - CSV 파일(`경부선상행`, `경부선하행`)을 통한 기차 시간표 초기 적재
   - 수어로 인식된 슬롯 데이터를 바탕으로 조건에 맞는 열차 시간표 검색 및 정렬
3. **예매 및 결제 시스템 (Backend + Frontend)**
   - 선택된 기차편에 대한 예매 생성 및 예매 번호(QR코드) 발급
   - 결제 상태 관리 및 환불 기능 지원
4. **사용자 친화적 키오스크 UI (Frontend)**
   - 실제 기차역 키오스크와 유사한 직관적인 UI/UX
   - 수어 인식 진행 상태 및 인식된 단어 실시간 피드백 표시

---

## 🚀 실행 방법 (Getting Started)

프로젝트를 로컬 환경에서 실행하기 위해 각 디렉토리의 지침을 따라주세요.

### 1. Backend (Spring Boot)

```bash
cd backend
# 의존성 설치 및 빌드
./gradlew clean build --refresh-dependencies
# 서버 실행 (H2 메모리 DB에 CSV 데이터가 자동 적재됩니다)
./gradlew bootRun
```
- API 서버 URL: `http://localhost:8080/api`
- Swagger 문서: `http://localhost:8080/api/swagger-ui/index.html`

### 2. Frontend (React)

```bash
cd frontend
# 의존성 설치
npm install
# 개발 서버 실행
npm run dev
```
- 프론트엔드 접속: 터미널에 표시된 `http://localhost:5173/` 등의 주소로 접속

### 3. AI Server (Python)

```bash
cd server
# 패키지 설치
pip install -r requirements.txt
# 실시간 인식 서버 실행
python app.py
```
- 모델 및 설정 파일 경로: `model_files/config.yaml`, `model_files/*.ckpt`
- macOS 사용 시 카메라 권한 확인 필수

---

## 🎯 향후 개발 계획

- 코레일(Korail), SRT 등 실제 외부 기차 API 연동
- 모바일(카카오톡 등) 예매 정보 및 QR 티켓 전송 기능
- AI 모델 정확도 향상을 위한 데이터 증강 및 실시간 손 위치 기반 고급 검증 로직 최적화
- JWT 기반 사용자 인증 및 보안 강화
