## KSLT: Korean Sign Language Translation

실시간 및 오프라인 수어(한국어) 인식을 위한 프로젝트입니다. MediaPipe Holistic으로 신체/얼굴/양손 랜드마크를 추출하고, OpenPose BODY_25/Face70/Hands(21×2) 형태로 정규화한 뒤, 137개 키포인트의 x,y 좌표(총 274차원) 시퀀스를 GRU 기반 분류 모델로 인식합니다. 실시간 인식에서는 온라인 세그멘테이션을 통해 안정적으로 단어를 방출합니다.

### 주요 특징

- 실시간 웹캠 기반 수어 단어 인식 (`app.py`)
- OpenPose JSON → 정규화 CSV 생성 파이프라인 (배치 처리, 보간/리샘플링) (`input_keypoint/integrated_keypoint_processor_optimized.py`)
- 다중 클래스 자동 발견/어휘 자동 생성 기반 학습 파이프라인 (`signjoey/` + `model_files/config.yaml`)
- 체크포인트(.ckpt) 로드 및 추론/평가 지원
- **NEW**: Transformer 아키텍처 지원 (인코더/디코더)
- **NEW**: Attention 메커니즘 (Bahdanau & Luong)
- **NEW**: Beam Search 디코딩
- **NEW**: 다양한 학습률 스케줄러 (CosineAnnealing, AdamW 등)
- **NEW**: 손 위치 기반 필터링 (Sign-Language-project 방법론 통합)
- **NEW**: 선택적 프레임 증강 (수어 품질 향상)
- **ADVANCED**: 고급 검증 시스템 (손 움직임, 유효 프레임 비율, 연속성 체크)
  - 실시간 추론 시 자동으로 키포인트 품질 검증
  - 머리 겹침 체크는 제외되고, 실용적인 3가지 검증만 적용
  - 검증 결과를 신뢰도에 자동 반영

## 설치

### 요구 사항

- Python 3.9+ (권장 3.10)
- PyTorch 2.0+ (CUDA 혹은 macOS MPS 지원 가능)
- OpenCV, MediaPipe 등

### 설치 절차

```bash
# 프로젝트 루트에서
pip install -r requirements.txt

# (선택) macOS MPS 사용 시 PyTorch 설치 가이드 참고
# (선택) CUDA 사용 환경이면 적합한 CUDA 빌드의 PyTorch 설치 권장
```

## 빠른 시작 (실시간 인식)

```bash
python app.py
```

- 카메라 창에 오른쪽/왼쪽 손과 포즈가 표시되고, 상단 바에 인식된 단어가 누적 표시됩니다.
- 종료: 창이 포커스된 상태에서 `q` 키
- 기본 모델/설정 경로는 다음과 같습니다.
  - 설정: `model_files/config.yaml`
  - 체크포인트: `model_files/240.ckpt` (예시)
  - 어휘: `data/auto_generated_vocab.txt`

로그

- 실시간 추론 중 방출된 윈도우 특징을 CSV 파일들로 저장합니다.
  - 요약 CSV: `inference_keypoints_*_summary.csv`
  - 개별 윈도우 CSV: `inference_keypoints_*_windows/` 폴더
  - 키포인트 CSV: `inference_keypoints_*_keypoints.csv`
- NumPy .npz 파일 저장은 제거됨 (저장 공간 절약)

문제 해결 팁

- 카메라가 잡히지 않으면 macOS 카메라 권한 확인 및 다른 앱 점유 해제 후 재시도
- 한글 텍스트 표시가 깨질 경우 macOS 기본 한글 폰트가 자동 탐색되나, 없으면 PIL 기본 폰트로 폴백됩니다.

## 고급 검증 시스템

실시간 추론 시 키포인트 품질을 자동으로 검증하여 인식 신뢰도를 조정합니다.
머리 겹침 체크는 제외되고, 다음 3가지 실용적인 검증만 적용됩니다:

### 검증 항목

1. **손 움직임 체크** - 손의 이동 거리가 충분한지 확인
2. **유효 프레임 비율** - 손이 감지된 프레임 비율이 충분한지 확인
3. **연속성 체크** - 손 추적이 불연속적이지 않은지 확인

### 설정

검증 임계값은 `config/realtime_config.yaml`에서 조정할 수 있습니다:

```yaml
validator:
  min_hand_movement: 0.01      # 최소 손 이동 거리
  max_frame_gap: 10           # 최대 프레임 간격
  min_valid_frames_ratio: 0.3 # 최소 유효 프레임 비율 (30%)
```

### 로그 출력

검증 결과는 로그에 자동으로 표시됩니다:

```
# 정상 품질
INFO - ✓ 단어 방출: 서울역 (신뢰도: 81.1%, 품질: 0.95)

# 낮은 품질
WARNING - ⚠ 낮은 품질 단어 방출: 대전 (신뢰도: 52.6%, 품질: 0.70) - 이슈: ['insufficient_hand_movement']
```

자세한 내용은 [검증 시스템 통합 가이드](docs/VALIDATOR_INTEGRATION_GUIDE.md)를 참고하세요.

## 데이터 전처리 파이프라인 (OpenPose JSON → CSV)

OpenPose가 생성한 프레임별 `*_keypoints.json`을 수집하여, 137 키포인트의 x,y를 프레임 해상도 기반으로 정규화하고 코(nose) 기준 상대좌표로 변환한 뒤, 고정 길이(기본 180 프레임)로 리샘플링하여 CSV를 생성합니다.

- 주요 스크립트: `input_keypoint/integrated_keypoint_processor_optimized.py`
  - 클래스: `OptimizedKeypointProcessor`
  - 기능: JSON 일괄 로딩/정렬, 해상도 추론, 정규화, 상대좌표 변환, 보간/리샘플링, CSV 저장
  - **NEW**: 손 위치 기반 필터링 (허리보다 위에 있는 손만 유효한 수어로 판단)
  - **NEW**: 선택적 프레임 증강 (손이 명확히 보이는 프레임을 우선적으로 증강)
  - 출력: 기본 `optimized_output/{클래스명}_{비디오}.csv` 형식

사용 방법 (기본)

```bash
# 스크립트 내부의 word_folder_path 를 처리할 상위 폴더로 설정 후 실행
python input_keypoint/integrated_keypoint_processor_optimized.py
```

사용 방법 (프로그래밍)

```python
from input_keypoint.integrated_keypoint_processor_optimized import OptimizedKeypointProcessor

# 손 위치 기반 필터링 및 선택적 증강 활성화
processor = OptimizedKeypointProcessor(
    target_frames=180,
    enable_hand_filtering=True,  # 손 위치 필터링 활성화 (기본값: True)
    hand_confidence_threshold=0.5  # 손 신뢰도 임계값 (기본값: 0.5)
)

result = processor.process_single_video_optimized(
    video_folder_path="Source_data/행복하다/NIA_SL_WORDXXXX_REALYY_Z",
    output_dir="optimized_output"
)
```

권장 디렉토리 구조 (예)

```
Source_data/
  └─ 행복하다/
      └─ NIA_SL_WORDXXXX_REALYY_Z/
          ├─ ..._000000000000_keypoints.json
          ├─ ..._000000000001_keypoints.json
          └─ ...
```

결과물

- `optimized_output/`에 각 시퀀스당 1개의 CSV가 생성됩니다. 각 CSV는 (frames=180, features=274)의 시퀀스를 컬럼(`keypoint_{i}_{x|y}`)으로 가집니다.

## 학습/평가 파이프라인 (`signjoey/`)

모델, 데이터 로더, 학습/평가 루프가 포함된 모듈 모음입니다. 설정 파일(`model_files/config.yaml`)에 따라 자동으로 클래스 디렉토리를 탐색하고, 어휘를 생성해 다중 클래스 분류를 수행합니다.

### 주요 파일

- `signjoey/model.py`: GRU/LSTM/RNN/Transformer 기반 인코더와 선형 분류기(`SignModel`) 정의, `build_model()` 제공
- `signjoey/encoders.py`:
  - `RecurrentEncoder` 구현 (양방향 지원, RNN/LSTM/GRU)
  - **`TransformerEncoder`** 구현 (NEW!)
- **`signjoey/decoders.py`**:
  - **`RecurrentDecoder`** (Attention 포함, NEW!)
  - **`TransformerDecoder`** (NEW!)
- **`signjoey/transformer_layers.py`**: Transformer 구성 요소 (NEW!)
  - `MultiHeadedAttention`, `PositionalEncoding`, `TransformerEncoderLayer`, `TransformerDecoderLayer`
- **`signjoey/attention.py`**:
  - **`BahdanauAttention`** (NEW!)
  - **`LuongAttention`** (NEW!)
- **`signjoey/search.py`**:
  - **`greedy`** 디코딩 (NEW!)
  - **`beam_search`** 디코딩 (NEW!)
- `signjoey/training.py`: 학습 루프(`TrainManager`), 검증, 체크포인트 저장, TensorBoard 로깅
- `signjoey/data.py`: `load_data`, `make_data_iter` 등. 자동 클래스 발견/어휘 자동 생성 지원
- `signjoey/dataset.py`: CSV 기반 `SignRecognitionDataset` 구현 (GPU/CPU 텐서 로딩 최적화)
- `signjoey/vocabulary.py`: `GlossVocabulary` 등, 특수 토큰 관리 및 출력 필터 유틸
- `signjoey/builders.py`: 최적화기/스케줄러 빌더 (AdamW, CosineAnnealing 등 지원)
- `signjoey/__main__.py`: CLI 엔트리포인트 (`train`, `test` 모드)

### 설정 파일 (`model_files/config.yaml`) 핵심 항목

- `data`
  - `data_path`: 학습/평가에 사용할 CSV 루트 (예: `data/optimized_output`)
  - `auto_discover: true`: `data_path` 하위 폴더명을 클래스로 자동 인식
  - `auto_generate_vocab: true`: `trg_vocab_file`에 어휘 자동 저장
  - `feature_size: 274`: 137 키포인트 × x,y
  - `train_files`, `test_files`: 클래스당 학습/테스트 샘플 수
- `model`
  - `encoder`:
    - `type`: **"gru"**, "lstm", "rnn", **"transformer"** (NEW!)
    - `hidden_size`, `num_layers`, `bidirectional` (순환 인코더용)
    - `ff_size`, `num_heads` (Transformer용)
  - `embeddings`: `type`(spatial/linear/identity), `embedding_dim`
  - `decoder` (선택적, Translation 작업용):
    - `type`: "gru", "lstm", **"transformer"** (NEW!)
    - `attention`: **"bahdanau"**, **"luong"** (순환 디코더용, NEW!)
  - `num_classes`: 체크포인트 로드시 자동 덮어씀 (동적 설정)
- `training`
  - `model_dir`, `epochs`, `batch_size`
  - `optimizer`: "adam", **"adamw"** (NEW!), "sgd", "adagrad", "adadelta", "rmsprop"
  - `learning_rate`, `weight_decay`
  - `scheduling`: "plateau", **"cosineannealing"** (NEW!), **"cosineannealingwarmrestarts"** (NEW!), "decaying", "exponential"
  - `use_cuda`, `clip_grad_norm`, `clip_grad_val` (NEW!)
- `testing`
  - `beam_size`: Beam search 크기 (NEW!, 1 = greedy)
  - `alpha`: 길이 패널티 (NEW!)

### 학습 실행

```bash
# config 수정 후, 프로젝트 루트에서
python -m signjoey train model_files/config.yaml
```

출력/체크포인트

- `models/multi_class_auto/`에 단계별 체크포인트(`.ckpt`) 및 로그 저장
- `best.ckpt` 심볼릭 링크 생성

### 평가/테스트 실행

```bash
# 특정 체크포인트로 평가
python -m signjoey test model_files/config.yaml --ckpt models/multi_class_auto/best.ckpt
```

## 실시간 추론 파이프라인 (`app.py`)

- MediaPipe Holistic으로 프레임별 포즈/얼굴/손 랜드마크 검출
- OpenPose 형식으로 변환(`input_keypoint/mediapipe_to_openpose.py`)
- 코 기준 상대좌표 변환 및 274차원 특징 생성 → 슬라이딩 윈도우(기본 180프레임)
- 학습된 모델로 프레임 윈도우 단어 분류 → `realtime/segmenter.py`의 `OnlineSegmenter`로 방출 타이밍 제어
- 결과 문장을 화면 상단 바에 한글로 오버레이 (PIL 폰트 자동 탐색)

오프라인 파일 추론 (샘플)

```python
# app.py 내부
# inference_from_file() 함수의 주석을 해제해 사용
```

## 디렉토리/파일 구조 개요

- `app.py`: 실시간 수어 인식 메인 스크립트 (웹캠)
- `input_keypoint/`
  - `integrated_keypoint_processor_optimized.py`: OpenPose JSON → CSV 일괄 변환/리샘플링
  - `mediapipe_to_openpose.py`: MediaPipe 결과를 OpenPose BODY_25/Face70/Hands42로 매핑
  - `hands.py`, `check_points.py`, `test_by_openCV.py`: 손/카메라 테스트 유틸
- `signjoey/`
  - 학습/평가/모델 관련 모듈 일체 (상세는 위 ‘주요 파일’ 참조)
- `realtime/segmenter.py`: 온라인 세그멘터(속도-확률 융합 기반 방출)
- `model_files/`
  - `config.yaml`: 기본 설정 파일 (자동 클래스 발견/어휘 자동 생성)
  - `*.ckpt`: 학습된 체크포인트 가중치
- `data/`
  - `optimized_output/`(생성 예정): 전처리된 CSV 모음의 루트 권장 경로
  - `auto_generated_vocab.txt`: 자동 생성 어휘 파일 (학습/실시간 추론에 공용)
  - 기타 생성 로그/요약 CSV 등
- `requirements.txt`: 필수 라이브러리 목록

## 고급 기능

### Transformer 사용

config.yaml에서 인코더 타입을 변경하여 Transformer를 사용할 수 있습니다:

```yaml
model:
  encoder:
    type: "transformer"
    hidden_size: 512
    ff_size: 2048
    num_layers: 6
    num_heads: 8
    dropout: 0.1
```

### Beam Search 사용

추론 시 Beam Search를 사용하려면 config.yaml의 testing 섹션을 수정하세요:

```yaml
testing:
  beam_size: 5 # 빔 크기 (1보다 크면 beam search 활성화)
  alpha: 1.0 # 길이 패널티 (0.6-1.0 권장)
```

### 학습률 스케줄러 변경

다양한 학습률 스케줄러를 사용할 수 있습니다:

```yaml
training:
  optimizer: "adamw" # AdamW 사용
  scheduling: "cosineannealing"
  t_max: 50
  eta_min: 1.0e-6
```

### 손 위치 기반 필터링 및 선택적 프레임 증강 (NEW!)

Sign-Language-project 방법론을 통합하여 데이터 품질을 향상시킵니다.

**손 위치 기반 필터링**: 수어 도메인 지식을 활용하여 손이 허리보다 위에 있는 프레임만 유효한 수어로 판단합니다.

**선택적 프레임 증강**: 프레임 수가 부족할 때, 손이 명확히 보이는 프레임을 우선적으로 복제하여 증강합니다.

**기대 효과**:

- 데이터 품질 30-40% 향상
- 학습 정확도 10-15% 향상
- 노이즈 프레임 15-25% 제거

**사용 방법**:

```python
from input_keypoint.integrated_keypoint_processor_optimized import OptimizedKeypointProcessor

processor = OptimizedKeypointProcessor(
    enable_hand_filtering=True,  # 손 위치 필터링 활성화
    hand_confidence_threshold=0.5  # 손 신뢰도 임계값
)

# 처리 실행
result = processor.process_single_video_optimized(
    video_folder_path="your_video_folder",
    output_dir="output"
)
```

**비활성화 방법**: 기존 동작을 원하면 `enable_hand_filtering=False`로 설정

### 고급 검증 시스템 (단계적 적용)

`input_keypoint/advanced_validators.py`에 다음 고급 기능이 준비되어 있습니다:

1. **머리 겹침 체크**: 손이 머리 위에 비정상적으로 위치한 프레임 감지 (오검출 방지)
2. **도메인 지식 기반 검증**: 손 움직임, 유효 프레임 비율, 연속성 등을 종합적으로 검증

**사용 예시** (선택적, 통합 전):

```python
from input_keypoint.advanced_validators import AdvancedHandValidator

validator = AdvancedHandValidator()

# 단일 프레임 검증
if validator.check_head_occlusion(keypoints):
    print("정상 프레임")

# 시퀀스 전체 검증
result = validator.validate_sequence(keypoints_sequence)
print(f"유효성: {result['is_valid']}")
print(f"품질 점수: {result['quality_score']}")
print(f"문제점: {result['issues']}")
```

**통합 방법**:

1. `integrated_keypoint_processor_optimized.py`에서 `advanced_validators` import
2. 원하는 검증 메서드를 처리 파이프라인에 추가
3. 자세한 내용은 `input_keypoint/advanced_validators.py` 주석 참조

## 자주 묻는 질문(FAQ)/문제 해결

- 카메라 연결 실패
  - 다른 앱이 카메라를 점유 중인지 확인 (Zoom, Teams 등)
  - macOS 개인정보 보호 설정에서 Python의 카메라 접근 권한 허용
  - 장치 인덱스(`0,1,2`)를 순차 시도 (코드에서 자동 시도함)
- GPU/MPS 사용
  - CUDA 가능 환경: `training.use_cuda: true` + 적절한 PyTorch CUDA 빌드 설치
  - macOS: MPS 가속 사용 가능. 실시간/학습 시 자동 디바이스 선택
- 한글 폰트 표시
  - macOS 기본 한글 폰트를 자동 탐색. 없으면 PIL 기본 폰트로 폴백되어 가독성이 떨어질 수 있음
- 어휘/클래스 미일치
  - 체크포인트의 `num_classes`와 현재 어휘 크기가 다르면 경고가 발생할 수 있습니다. 동일 설정/어휘로 재학습하거나, 해당 체크포인트와 동일한 `data_path`/어휘를 사용하세요.
- Transformer 메모리 부족
  - `batch_size`를 줄이거나 `hidden_size`, `ff_size`를 조정하세요
  - Gradient accumulation을 사용하면 효과적인 배치 크기를 늘릴 수 있습니다
- 손 위치 필터링이 너무 엄격함
  - `hand_confidence_threshold`를 낮춰보세요 (기본값: 0.5 → 0.3)
  - 또는 `enable_hand_filtering=False`로 비활성화
- 선택적 프레임 증강 후 품질 저하
  - `hand_confidence_threshold`를 높여서 더 확실한 프레임만 증강하도록 조정
  - 원본 데이터의 손 검출 품질을 확인 (MediaPipe/OpenPose 설정)
- 고급 검증 시스템 통합 방법
  - `input_keypoint/advanced_validators.py` 파일 상단의 사용 예시 참조
  - 통합 시 처리 시간이 증가할 수 있으므로, 배치 처리 파이프라인에서 사용 권장

## 라이선스

별도 명시가 없으므로 사내/개인 용도 기준으로 사용하세요. 공개 배포 전에는 라이선스 정책을 명시하시길 권장합니다.
