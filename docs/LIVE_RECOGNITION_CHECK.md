# 실제 인식 경로 연결 검증

## 확인 범위

2026-09-18 Windows CPU 환경에서 FE의 실제 RecognitionSession 코드를 Node로 실행하고,
실제 Spring Boot → Python Flask → ONNX 모델을 연결해 검증했다.
모의 AI 응답이 아닌 실제 모델 추론을 사용했다.

**입력은 합성 키포인트다. 수어 인식 정확도, 브라우저 카메라, MediaPipe 변환, React Hook의 재접속 동작을 검증한 결과는 아니다.**

- 서로 다른 두 BE 세션 ID와 AI 시작 ACK
- 두 사용자의 128프레임 교차 전송 및 대상별 RESULT 수신
- A RESET 후 frameIndex 0 재시작, B의 버퍼·revision 유지
- 오래된 revision과 다른 사용자의 ID를 넣은 요청 거절
- A END 후에도 B 추론 유지
- 실제 AI 프로세스 단절 시 두 사용자에게 AI_UNAVAILABLE 전달
- AI 재기동 후 BE가 자동 재접속하고 새 세션에서 동일 테스트 통과
- 테스트 프로세스의 유휴 제한을 3초로 설정했을 때 SESSION_EXPIRED 전달
- 테스트 종료 후 기본 유휴 제한 120초 복원

첫 단절 검증 시도는 로컬 프로세스 종료 명령 오류로 제한 시간을 넘겼다.
프로세스를 확인하고 종료한 재실행에서는 단절 검증이 통과했다.

### 이후 확인 기록 (2026-09-22 문서 갱신)

- [PR #15](https://github.com/doukdoll/sign_language_ver.2/pull/15) 병합 전 소유자가 브라우저 카메라 확인 완료를 알렸다. 자동 합성 입력 테스트와 별개의 사용자 확인 기록이며, 항목별 측정 로그나 정확도 수치는 없다.
- [PR #17](https://github.com/doukdoll/sign_language_ver.2/pull/17)에서 카메라 스트림 종료와 결제 타이머 정리를 수정했다. 이 변경 이후 카메라·결제 UI의 수동 재검증은 기록되지 않았다.
- [CI](CI.md)에서 FE·BE·AI 모델 없는 테스트 및 FE·BE 빌드가 통과했다. CI는 아래 live ONNX·카메라 검사를 실행하지 않는다.

### 코드 정리 후 재검증 (2026-09-22)

- 별도 로컬 포트(AI 15001, BE 18080)에서 수정된 서버와 실제 Attention ONNX를 기동하고 `npm run test:recognition:live -- ws://127.0.0.1:18080/api/sign/stream`이 통과했다.
- 두 세션 교차 추론·대상별 결과·RESET 격리·오래된 revision/위조 ID 거절·한 세션 END 이후 다른 세션 유지까지 확인했다. 단절·재기동·유휴 만료는 이번 실행에서 다시 검증하지 않았다.
- HTTP와 WebSocket의 공통 예측 함수를 실제 ONNX로 동시 호출하여 공유 잠금과 기존 결과 유지를 확인했다. HTTP DEPARTURE/ARRIVAL 필드 매핑도 확인했다.
- 카메라 단일 스트림 소유·지연 초기화 종료·전송 중 정리·장치 연결 종료는 모의 객체 테스트로 확인했다. 실제 브라우저 카메라·왕복 화면 조작은 미검증이다.
- 모델 파일, 전처리와 128/180 입력 정책은 바꾸지 않았다. 위 합성 입력 검증은 정확도 평가가 아니다.

## 검증 환경

| 항목 | 값 |
| --- | --- |
| Python | 3.10.21, 프로젝트 전용 venv |
| PyTorch | 2.14.0+cpu |
| NumPy / pandas | 1.24.4 / 2.0.3 |
| ONNX Runtime | 1.23.2, CPU |
| Flask / flask-sock / simple-websocket | 3.1.2 / 0.7.0 / 1.1.0 |
| PyYAML | 6.0.3 |
| Java / Gradle | 17.0.19 / 8.14.4 |
| Node.js | 24.18.0 |
| 모델 | deployment/20251109-1439_Attention/20251109-1439.onnx |
| 모델 SHA-256 | 322eda144b2f26b44f57160c7b66b1c7be0217da2820ea06df045f96944368ed |

기존 모델·가중치·전처리·128/180 프레임 정책은 변경하지 않았다.
서버 실행에 필요한 최소 의존성만 설치했고 전체 requirements.txt 설치는 검증하지 않았다.
requirements-smoke.txt는 직접 의존성 목록이며 전체 전이 의존성 lockfile은 아니다.
실행 환경에서 pip check는 통과했다.

## 재현 방법 (PowerShell)

Python 3.10, JDK 17, Gradle 8.14.4, Node.js 24를 준비한다.
현재 저장소에는 Gradle wrapper JAR가 없으므로 설치된 Gradle을 사용한다.

AI 환경 준비 — 저장소 루트:

```powershell
py -3.10 -m venv server/venv
server/venv/Scripts/python.exe -m pip install torch==2.14.0+cpu --index-url https://download.pytorch.org/whl/cpu
server/venv/Scripts/python.exe -m pip install -r server/requirements-smoke.txt
server/venv/Scripts/python.exe -m pip check
```

터미널 1 — AI (로컬 주소에만 바인딩):

```powershell
cd server
./venv/Scripts/python.exe -X utf8 -c "import ai_server; assert ai_server.SERVICE is not None; ai_server.app.run(host='127.0.0.1', port=5001, debug=False)"
```

터미널 2 — BE:

```powershell
cd backend
gradle bootJar
java -jar build/libs/sign-language-transport-backend-0.0.1-SNAPSHOT.jar --server.address=127.0.0.1 --spring.profiles.active=test
```

test 프로필은 열차 CSV 자동 적재를 생략하고 H2 인메모리 DB를 사용한다.
여기서는 인식 연결만 검증하며 열차 검색·예매 데이터 검증은 포함하지 않는다.

터미널 3 — 합성 데이터 연결 검증:

```powershell
cd frontend
npm ci
npm run test:recognition:live
```

주소 변경: `npm run test:recognition:live -- ws://127.0.0.1:8080/api/sign/stream`

- 단절 검증: `npm run test:recognition:live -- --expect-disconnect` 실행 후 READY 출력 시 **테스트 AI 서버만** 종료한다. 30초 안에 오류가 전달되어야 한다. AI를 다시 실행하고 기본 검증을 재실행한다.
- 만료 검증: 별도 AI 테스트 프로세스에서 app.run 전에 `ai_server.realtime_config['session_idle_timeout'] = 3.0`을 설정하고 `npm run test:recognition:live -- --expect-expiry`를 실행한다. 끝나면 그 프로세스를 종료하고 기본 설정으로 다시 실행한다. 저장소 YAML은 변경하지 않는다.
- 기본 `npm test`는 서버가 필요 없는 단위 테스트이며 live 테스트와 분리돼 있다.

## 카메라 수동 재검증 단계

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort
```

1. 브라우저에서 http://127.0.0.1:5173/departure 에 접속하고 카메라 권한을 허용한다.
2. 실제 수어로 출발역을 입력하고 결과가 표시되는지 확인한다.
3. 다시 인식하기를 누른 직후 이전 결과가 사라지고 새 동작의 결과만 표시되는지 확인한다.
4. 맞아요를 눌러 도착역 화면으로 이동하고 도착역 인식을 확인한다.
5. AI를 재시작했을 때 화면의 오류·결과 초기화·재접속을 확인한다.
6. 두 카메라를 사용할 수 있다면 두 브라우저에서 A의 재시도가 B를 방해하지 않는지 확인한다.
7. 권한 거부 또는 카메라 분리 후 오류가 표시되는지 확인하고, 권한·연결을 복구한 뒤 다시 인식하기로 재시작한다.
8. 권한 응답이나 모델 초기화가 끝나기 전에 페이지를 떠났을 때 카메라 사용 표시가 남지 않는지 확인한다.

한 카메라의 여러 탭 동시 사용은 브라우저·장치에 따라 제한될 수 있다.
사용자 간 서버 격리는 위 합성 데이터 테스트로 별도 확인했다.
코드 변경 후에는 필요한 항목을 다시 확인하고 확인자·커밋·실행 환경을 기록한다. 이전 소유자 확인이나 합성 입력 테스트만으로 현재 커밋의 모든 카메라 E2E 항목이 검증됐다고 표시하지 않는다.
