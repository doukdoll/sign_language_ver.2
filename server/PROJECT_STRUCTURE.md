# AI 서버 프로젝트 구조

웹 서비스 진입점은 `ai_server.py`, PC 카메라 전용 진입점은 `app.py`입니다. 설치·요청 예시는 [README](README.md), 메시지 규약은 [실시간 인식 규약](../docs/RECOGNITION_PROTOCOL.md)을 참고합니다.

## 주요 파일

```text
server/
├── ai_server.py                  # Flask HTTP /predict_keypoints, WS /ws/predict
├── ai_server_faster.py           # 실험용 서버 변형
├── ai_server_add_log.py          # 실험용 서버 변형
├── app.py                        # 로컬 카메라 실행
├── config/
│   ├── realtime_config.yaml      # 기본 실시간 설정
│   └── test_config.yaml          # 수동 테스트 설정 (모델 경로 수정 필요)
├── deployment/
│   ├── inference_service.py      # 공통 추론 인터페이스, ONNX 길이 보정
│   ├── 20251109-1439_Attention/   # 기본 모델, 어휘, 기존 검증 메타데이터
│   └── 20251109-1439_GRU/         # 비교용 모델, 어휘, 기존 검증 메타데이터
├── realtime/
│   ├── http_api.py               # 모델 독립 Flask factory, HTTP 입력·오류 경계
│   ├── sessions.py               # 연결·세션별 버퍼, revision, ACK, 만료
│   ├── app_main.py               # 로컬 카메라 파이프라인
│   ├── inference_utils.py        # 모델 로드·온라인 정규화
│   ├── segmenter.py              # 로컬 카메라 단어 방출 판정
│   ├── inference_logger.py       # 추론 기록
│   └── visualization.py          # 표시 유틸리티
├── input_keypoint/
│   ├── mediapipe_to_openpose.py
│   ├── bodypart_normalization_processor.py  # OpenPose JSON → 정규화 CSV
│   ├── advanced_validators.py    # 로컬 시퀀스 품질 점검
│   └── hand_filtering.py
├── signjoey/                     # 학습·평가 코드 (데이터·완성 설정 별도)
├── tests/
│   ├── test_http_api.py          # Flask test client를 사용하는 HTTP 테스트 15개
│   ├── test_sessions.py          # 표준 라이브러리만 사용하는 자동 테스트
│   └── test_realtime_inference.py # 모델·카메라 수동 진단 도구
├── docs/                         # 정규화·로컬 검증기 가이드
├── utils/                        # 설정, 로깅, 성능, 예외 처리
├── requirements.txt              # 기존 전체 의존성 (headless OpenCV 포함)
├── requirements-smoke.txt        # CPU 서비스 스모크용 최소 의존성
├── requirements-test.txt         # 모델 없는 HTTP 테스트용 Flask
└── Dockerfile                    # Python 3.10, ai_server.py 실행
```

## 경로별 입력 처리

| 실행 경로 | 수집·추론 입력 | 주요 차이 |
| --- | --- | --- |
| Flask WebSocket | 세션마다 128프레임 수집, 이후 5프레임마다 추론 | 모델 서비스에서 180까지 0 padding, 세션 규약 검증 |
| Flask HTTP | 요청의 한 프레임을 128번 반복 | 모델 서비스에서 180까지 0 padding, 단일 프레임 진단 성격 |
| `app.py` 로컬 카메라 | ONNX 모드 버퍼 128프레임 | 품질 검증기·세그멘터 사용, 별도 GUI 환경 필요 |
| 수동 카메라 테스트 | `test_config.yaml`의 윈도우 사용 | 기본 YAML의 없는 모델 경로를 먼저 수정 |

`realtime_config.yaml`에 `window_size: 180`이 있어도 현재 Flask 및 `app.py`의 ONNX 분기는 128을 고정 사용합니다. ONNX 모델 자체 입력은 180 × 274입니다. 버퍼 크기와 모델 입력 길이를 구분해야 합니다.

HTTP와 WebSocket은 `ai_server.predict_window()`의 동일 잠금으로 공유 모델을 호출합니다. `realtime.http_api.create_app()`에는 전처리·한 프레임 추론·준비 상태 확인 함수를 주입하며, HTTP 어댑터 자체는 모델이나 카메라를 로드하지 않습니다.

HTTP 입력 오류는 400, 모델 미준비는 503, 추론 실패는 500으로 반환합니다. 오류 본문은 `errorCode`·`errorMessage`이며 내부 예외를 포함하지 않습니다. 성공 응답은 `recognitionTarget`에 맞는 `departureCity`/`arrivalCity` 필드만 채웁니다. target 생략은 기존 `DEPARTURE` 기본값을 유지합니다.

웹 서비스의 미사용 `AdvancedHandValidator` 초기화·인자는 제거했지만, `app.py` 경로의 품질 검증기·세그멘터와 학습·실험 파일은 유지합니다.

출력 클래스는 모델별 `vocabulary.txt`가 기준입니다. Attention은 `서울`, GRU는 같은 인덱스에 `서울역`을 사용합니다. 자세한 기존 지표와 클래스는 [배포 모델 문서](deployment/README.md)를 참고합니다.

## 자동 검증

```bash
# server 디렉터리에서, 외부 패키지 설치 없이 실행
python -S -m unittest tests.test_sessions -v

# Flask HTTP 경계만 추가 검사: torch/ONNX/카메라 패키지는 불필요
python -m pip install -r requirements-test.txt
python -m unittest tests.test_http_api -v
```

세션 15개와 HTTP 15개는 현재 코드의 로컬 검증에서 통과했습니다. [CI](../.github/workflows/ci.yml)는 두 단계를 실행하며, 원격 결과는 [PR #20](https://github.com/doukdoll/sign_language_ver.2/pull/20)의 최종 커밋 Checks에서 확인합니다. 이전 PR #18 성공 기록은 신규 HTTP 테스트까지 실행했다는 뜻은 아닙니다. 실제 모델 연결과 카메라 점검은 [별도 실행 기록](../docs/LIVE_RECOGNITION_CHECK.md)을 참고합니다. 합성 입력 연결 검증은 정확도 평가가 아닙니다.

## 남아 있는 실험·기록의 범위

- `realtime.app_main.inference_from_file()`는 현재 없는 과거 PyTorch 모델 경로를 하드코딩하므로 그대로 실행하는 가이드가 아닙니다. 현재 ONNX 직접 추론 예시는 [배포 모델 문서](deployment/README.md)를 사용합니다.
- 과거 문서의 `multi_class_auto`, `20251014-202250`, `scripts/compare_normalization_methods.py`는 현재 저장소에 없습니다.
- [CHANGES](CHANGES.md)와 [검증기 통합 요약](.validator_integration_summary.md)은 2025년 작업 기록이며 최신 테스트 결과가 아닙니다.
- 학습 데이터와 완성된 학습 설정은 포함되지 않습니다. 정규화·입력 정책 변경 효과는 별도 데이터와 평가로 확인해야 합니다.
