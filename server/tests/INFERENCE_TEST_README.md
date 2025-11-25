# 추론 모델만으로 실시간 수어 인식 테스트

이 문서는 추론 모델만을 사용하여 실시간 수어 인식을 테스트하는 방법을 설명합니다.

## 개요

기존의 복잡한 실시간 시스템에서 세그멘테이션, 로깅, 성능 최적화 등의 기능을 제거하고, 순수하게 모델 추론만을 테스트할 수 있는 간소화된 시스템입니다.

## 파일 구조

```
KSLT/
├── tests/
│   ├── test_realtime_inference.py    # 메인 테스트 스크립트
│   └── INFERENCE_TEST_README.md      # 이 문서
├── config/
│   └── test_config.yaml              # 테스트 설정 파일
└── run_inference_test.sh             # 실행 스크립트 (프로젝트 루트)
```

## 주요 기능

### 1. 샘플 데이터 테스트

- 다양한 패턴의 가상 데이터로 모델 추론 성능 테스트
- 랜덤 데이터, 영점 데이터, 일정한 값, 정규분포 등

### 2. 실시간 카메라 테스트

- 카메라 입력을 통한 실시간 키포인트 추출
- MediaPipe를 사용한 포즈/얼굴/손 랜드마크 감지
- 실시간 모델 추론 및 결과 표시

### 3. 설정 기반 테스트

- YAML 설정 파일을 통한 유연한 테스트 구성
- 모델 경로, 카메라 설정, 시각화 옵션 등

### 4. 신체 부위별 정규화

- **Pose**: 전체 화면 기준 정규화 (기존 방식)
- **Face**: 얼굴 바운딩 박스 기준 정규화 (디테일 강화)
- **Hands**: 각 손의 바운딩 박스 기준 정규화 (수어 핵심 동작 강화)
- 설정을 통해 기본 정규화 방식과 선택 가능

## 사용 방법

### 1. 기본 실행

```bash
# 가상환경 활성화
source .venv/bin/activate

# 전체 테스트 실행 (샘플 데이터 + 실시간)
# 프로젝트 루트에서 실행
python -m tests.test_realtime_inference

# 또는 tests 폴더에서 직접 실행
cd tests
python test_realtime_inference.py
```

### 2. 개별 테스트 실행

```bash
# 샘플 데이터 테스트만
python -m tests.test_realtime_inference --sample-only

# 실시간 카메라 테스트만
python -m tests.test_realtime_inference --realtime-only
```

### 3. 설정 파일 지정

```bash
# 사용자 정의 설정 파일 사용 (프로젝트 루트 기준 경로)
python -m tests.test_realtime_inference --config config/my_config.yaml
```

### 4. 간편 실행 (프로젝트 루트에서)

```bash
# 프로젝트 루트에서 직접 실행
cd /Users/parknohyeon/WorkSpace/Python/KSLT
source .venv/bin/activate && python -m tests.test_realtime_inference
```

## 설정 파일 (config/test_config.yaml)

### 모델 설정

```yaml
model:
  path: "deployment/multi_class_auto/multi_class_auto_model.pt"
  vocab_path: "deployment/multi_class_auto/vocabulary.txt"
  type: "pytorch" # pytorch 또는 onnx
  device: "auto" # auto, cpu, cuda, mps
```

### 실시간 설정

```yaml
realtime:
  window_size: 200 # 슬라이딩 윈도우 크기
  fps_target: 30.0 # 목표 FPS

  camera:
    indices: [0, 1, 2] # 시도할 카메라 인덱스
    width: 640
    height: 480
    fps: 30

  mediapipe:
    min_detection_confidence: 0.5
    min_tracking_confidence: 0.5

  # 키포인트 정규화 설정
  normalization:
    enable_bodypart_norm: true # 신체 부위별 정규화 활성화
    confidence_threshold: 0.3 # 유효한 키포인트 판별 임계값
    bbox_padding: 0.1 # 바운딩 박스 패딩 비율 (10%)
    image_width: 640 # 기본 이미지 너비
    image_height: 480 # 기본 이미지 높이
```

### 테스트 설정

```yaml
test:
  sample_data_tests:
    - name: "랜덤 데이터"
      type: "random"
      params:
        mean: 0.0
        std: 1.0

  realtime_test:
    show_landmarks: true
    show_confidence: true
    show_fps: true
    log_interval: 30
    top_k_predictions: 3
```

## 출력 예시

### 샘플 데이터 테스트

```
--- 랜덤 데이터 테스트 ---
예측 결과: 안녕하세요
신뢰도: 45.23%
상위 5개 예측:
  1. 안녕하세요: 45.23%
  2. 감사합니다: 23.45%
  3. 죄송합니다: 12.34%
  4. 좋아요: 8.90%
  5. 아니요: 5.67%
```

### 실시간 테스트

```
실시간 추론 테스트 시작 (종료: 'q' 키)
예측: 안녕하세요 (67.8%) - 추론시간: 15.2ms
상위 3개 예측:
  1. 안녕하세요: 67.8%
  2. 감사합니다: 18.4%
  3. 죄송합니다: 7.2%
```

## 주요 특징

### 1. 단순화된 구조

- 기존 시스템의 복잡한 세그멘테이션 로직 제거
- 순수한 모델 추론에 집중
- 최소한의 전처리와 후처리

### 2. 유연한 설정

- YAML 기반 설정으로 쉬운 커스터마이징
- 다양한 테스트 케이스 지원
- 시각화 옵션 제어

### 3. 성능 측정

- 실시간 FPS 측정
- 추론 시간 측정
- 메모리 사용량 모니터링 (선택적)

### 4. 오류 처리

- 카메라 연결 실패 시 자동 재시도
- 다양한 카메라 인덱스 지원
- 상세한 오류 메시지

### 5. 신체 부위별 정규화

- **차별화된 정규화**: 각 신체 부위별로 최적화된 정규화 방식 적용
- **바운딩 박스 기반**: 얼굴과 손의 세밀한 동작을 위한 바운딩 박스 기준 정규화
- **설정 가능**: YAML 설정을 통해 정규화 방식 선택 및 파라미터 조정
- **성능 향상**: 수어 인식의 핵심인 손 동작에 특화된 정규화

## 문제 해결

### 카메라 연결 문제

```bash
# 다른 앱에서 카메라 사용 중인지 확인
# 시스템 설정 > 보안 및 개인 정보 보호 > 카메라에서 Python 권한 확인
```

### 모델 로딩 실패

```bash
# 모델 파일 경로 확인
ls -la deployment/multi_class_auto/

# 어휘 사전 파일 확인
cat deployment/multi_class_auto/vocabulary.txt
```

### 성능 문제

```yaml
# 설정 파일에서 디바이스 변경
model:
  device: "cpu" # GPU 사용 시 문제가 있는 경우
```

### 정규화 설정 문제

```yaml
# 신체 부위별 정규화 비활성화 (기본 정규화 사용)
realtime:
  normalization:
    enable_bodypart_norm: false

# 정규화 파라미터 조정
realtime:
  normalization:
    confidence_threshold: 0.5  # 더 엄격한 임계값
    bbox_padding: 0.2         # 더 큰 패딩
```

## 기존 시스템과의 차이점

| 기능         | 기존 시스템                | 테스트 시스템          |
| ------------ | -------------------------- | ---------------------- |
| 세그멘테이션 | 복잡한 온라인 세그멘테이션 | 단순한 슬라이딩 윈도우 |
| 로깅         | 상세한 추론 로깅           | 최소한의 로깅          |
| 성능 최적화  | 메모리 모니터링, 동적 조정 | 기본적인 성능 측정     |
| 설정         | 복잡한 계층적 설정         | 단순한 YAML 설정       |
| 정규화       | 기본 정규화                | 신체 부위별 정규화     |
| 목적         | 실제 서비스용              | 모델 테스트용          |

## 다음 단계

1. 모델 성능 검증
2. 다양한 입력 패턴 테스트
3. 실시간 성능 최적화
4. 실제 서비스 통합

## 참고사항

- 이 테스트 시스템은 모델의 기본적인 추론 성능을 검증하기 위한 것입니다
- 실제 서비스에서는 추가적인 세그멘테이션과 후처리가 필요할 수 있습니다
- 카메라 권한과 하드웨어 사양에 따라 성능이 달라질 수 있습니다
