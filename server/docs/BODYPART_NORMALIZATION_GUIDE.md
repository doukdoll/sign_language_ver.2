# 신체 부위별 정규화 가이드

## 📋 개요

이 문서는 KSLT 프로젝트에 적용된 **신체 부위별 정규화 (Body-Part Normalization)** 기법에 대한 상세 가이드입니다.

### 🎯 목적

- 수어 인식의 핵심인 **손 동작의 미세한 차이**를 더 명확하게 표현
- **얼굴 표정**(비수지 신호)의 디테일 보존
- 전체적인 **모델 학습 효율** 향상

### 📊 기대 효과

- Winston1214 프로젝트 실험 결과: **BLEU +5.9%, Accuracy +5.5%**
- 손 특징 해상도: **약 33배 향상**
- 얼굴 특징 해상도: **약 33배 향상**

---

## 🔍 기존 방식 vs 신체 부위별 정규화

### 기존 방식 (글로벌 정규화)

```python
# 모든 137개 키포인트에 동일한 정규화 적용
normalized_x = keypoint_x / image_width   # 0 ~ 1 범위
normalized_y = keypoint_y / image_height  # 0 ~ 1 범위
```

**문제점:**

- 손과 얼굴은 전체 화면의 3~5%만 차지 → 정규화 후 0.03 범위에 압축
- 손가락의 미묘한 움직임이 0.001 수준의 변화로 축소
- 모델이 작은 수치 변화를 학습하기 어려움

### 신체 부위별 정규화

```python
# Pose: 전체 화면 기준 (기존과 동일)
pose_normalized = pose / [image_width, image_height]

# Face: 얼굴 바운딩 박스 기준
face_normalized = (face - face_bbox_min) / face_bbox_size  # 0 ~ 1 범위로 확장

# Hands: 각 손의 바운딩 박스 기준
hand_normalized = (hand - hand_bbox_min) / hand_bbox_size  # 0 ~ 1 범위로 확장
```

**장점:**

- 각 부위의 특징이 모두 0~1 범위로 **균등하게** 확장
- 손가락 움직임이 명확한 수치 변화로 표현
- 학습 시 gradient가 충분히 커서 빠른 수렴

---

## 🚀 사용 방법

### 1. 단일 비디오 폴더 처리

```python
from input_keypoint.bodypart_normalization_processor import process_video_with_bodypart_norm

# OpenPose JSON 파일들이 있는 폴더 처리
result = process_video_with_bodypart_norm(
    video_folder_path="Source_data/행복하다/NIA_SL_WORD0001_REAL01_A",
    output_dir="bodypart_norm_output",
    confidence_threshold=0.3,  # confidence 임계값
    bbox_padding=0.1,          # 바운딩 박스 패딩 10%
    enable_multiprocessing=True,
    max_workers=4
)

print(f"생성된 CSV: {result['csv_path']}")
```

### 2. 다중 비디오 폴더 일괄 처리

```python
from input_keypoint.bodypart_normalization_processor import BodyPartNormalizationProcessor
import os

# 프로세서 초기화
processor = BodyPartNormalizationProcessor(
    image_width=1920,
    image_height=1080,
    target_frames=180,
    confidence_threshold=0.3,
    bbox_padding=0.1
)

# 여러 폴더 처리
word_folder = "Source_data/행복하다"
video_folders = [
    os.path.join(word_folder, d)
    for d in os.listdir(word_folder)
    if os.path.isdir(os.path.join(word_folder, d))
]

for video_folder in video_folders:
    try:
        result = processor.process_single_video_optimized(
            video_folder,
            output_dir="bodypart_norm_output"
        )
        print(f"✓ {result['folder_name']}: {result['csv_path']}")
    except Exception as e:
        print(f"✗ {os.path.basename(video_folder)}: {e}")
```

### 3. 명령줄에서 직접 실행

```bash
# 프로젝트 루트에서
cd /Users/parknohyeon/WorkSpace/Python/KSLT

# 단일 단어 폴더 처리
python input_keypoint/bodypart_normalization_processor.py

# (내부에서 word_folder_path를 수정하여 사용)
```

---

## 🔧 주요 파라미터 설정

### BodyPartNormalizationProcessor 초기화 파라미터

| 파라미터                 | 기본값      | 설명                                                 |
| ------------------------ | ----------- | ---------------------------------------------------- |
| `image_width`            | 1920        | 기본 이미지 너비 (JSON에서 해상도 추출 실패 시 사용) |
| `image_height`           | 1080        | 기본 이미지 높이                                     |
| `target_frames`          | 180         | 리샘플링 목표 프레임 수                              |
| `confidence_threshold`   | 0.3         | 유효한 키포인트 판별 임계값                          |
| `bbox_padding`           | 0.1         | 바운딩 박스 패딩 비율 (0.1 = 10%)                    |
| `enable_multiprocessing` | True        | 멀티프로세싱 활성화 여부                             |
| `max_workers`            | CPU 코어 수 | 최대 워커 수                                         |

### confidence_threshold 조정 가이드

```python
# 엄격한 기준 (높은 품질만 사용)
confidence_threshold=0.5  # 손/얼굴 감지 실패 가능성 증가

# 권장 기준 (균형)
confidence_threshold=0.3  # 대부분의 경우 적절

# 느슨한 기준 (낮은 품질도 포함)
confidence_threshold=0.1  # 노이즈 포함 가능성 증가
```

### bbox_padding 조정 가이드

```python
# 패딩 없음 (정확한 바운딩 박스)
bbox_padding=0.0  # 경계 잘림 위험

# 권장 패딩 (10%)
bbox_padding=0.1  # 경계 여유 확보

# 큰 패딩 (20%)
bbox_padding=0.2  # 주변 맥락 포함, 정규화 효과 감소
```

---

## 📈 성능 비교

### 비교 스크립트 실행

```bash
cd /Users/parknohyeon/WorkSpace/Python/KSLT

# 비교 분석 및 시각화 생성
python scripts/compare_normalization_methods.py
```

**생성 결과:**

- `normalization_comparison.png`: 시각적 비교 차트
- 콘솔 출력: 특징 공간 분석 통계

### 예상 결과 예시

```
[Left Hand]
  글로벌 정규화: X 범위=0.0312, Y 범위=0.0298
  부위별 정규화: X 범위=1.0000, Y 범위=1.0000
  개선 비율: X=32.05배, Y=33.56배

[Right Hand]
  글로벌 정규화: X 범위=0.0287, Y 범위=0.0301
  부위별 정규화: X 범위=1.0000, Y 범위=1.0000
  개선 비율: X=34.84배, Y=33.22배
```

---

## ⚠️ 주의사항 및 제한사항

### 1. Fallback 로직

손이나 얼굴이 감지되지 않으면 자동으로 전체 화면 기준 정규화로 폴백:

```python
if valid_hand_points < 5:
    # 손 감지 실패 → 전체 화면 기준 정규화
    normalized[hand_range] = keypoints[hand_range] / [width, height]
```

### 2. 데이터 일관성

- **학습과 추론에 동일한 정규화 방식 적용 필수**
- 기존 데이터로 학습한 모델은 **재학습 필요**
- 모든 데이터를 재전처리해야 함

### 3. 처리 시간

- 바운딩 박스 계산으로 인해 약간의 오버헤드 발생
- 멀티프로세싱으로 대부분 상쇄됨

### 4. 상대 좌표 변환과의 호환성

현재 구현은 **Pose만 코 기준 상대 좌표로 변환**합니다:

```python
# Pose 부분만 상대 위치로 변환
relative_keypoints[0:25, :2] -= nose_keypoint[:2]

# Face, Hands는 바운딩 박스 기준이므로 그대로 유지
```

---

## 🔄 기존 코드와의 통합

### signjoey/dataset.py 수정 예시

```python
# 기존
from input_keypoint.integrated_keypoint_processor_optimized import OptimizedKeypointProcessor

# 신체 부위별 정규화 사용
from input_keypoint.bodypart_normalization_processor import BodyPartNormalizationProcessor

class SignRecognitionDataset(Dataset):
    def __init__(self, ...):
        # 프로세서 선택
        if use_bodypart_norm:
            self.processor = BodyPartNormalizationProcessor(...)
        else:
            self.processor = OptimizedKeypointProcessor(...)
```

### config.yaml에 설정 추가

```yaml
data:
  data_path: "bodypart_norm_output" # 신체 부위별 정규화 결과 경로
  normalization_method: "bodypart" # "global" or "bodypart"
  confidence_threshold: 0.3
  bbox_padding: 0.1
```

---

## 📊 실험 권장 사항

### 1단계: 소규모 테스트

1. 1~2개 단어 폴더로 데이터 전처리
2. 짧은 epoch (10~20)으로 학습
3. 기존 방식과 성능 비교

### 2단계: 하이퍼파라미터 튜닝

- `confidence_threshold`: 0.2, 0.3, 0.4 비교
- `bbox_padding`: 0.05, 0.1, 0.15 비교
- 학습률, 배치 크기 조정

### 3단계: 전체 데이터 적용

- 모든 데이터 재전처리 (시간 소요)
- Full training run
- 최종 성능 평가

---

## 🐛 문제 해결

### 문제: "유효한 키포인트가 없습니다" 오류

**원인:** JSON 파일에 키포인트 데이터가 없거나 손상됨

**해결:**

```python
# JSON 파일 검증
import json
with open('problematic.json', 'r') as f:
    data = json.load(f)
    print(data['people'])  # 데이터 확인
```

### 문제: 손/얼굴이 계속 fallback으로 처리됨

**원인:** confidence_threshold가 너무 높음

**해결:**

```python
# threshold 낮추기
processor = BodyPartNormalizationProcessor(
    confidence_threshold=0.2  # 0.3 → 0.2
)
```

### 문제: 정규화 후 값이 음수거나 1보다 큼

**원인:** bbox_padding이 너무 크거나 바운딩 박스 계산 오류

**해결:**

```python
# 패딩 줄이기
bbox_padding=0.05  # 0.1 → 0.05

# 또는 결과를 [0, 1]로 클립
normalized = np.clip(normalized, 0.0, 1.0)
```

---

## 📚 참고 자료

### 논문

- Winston1214 et al., "Keypoint based Sign Language Translation without Glosses" (2022)
  - arXiv: https://arxiv.org/abs/2204.10511

### 관련 코드

- `input_keypoint/bodypart_normalization_processor.py`: 신체 부위별 정규화 구현
- `input_keypoint/integrated_keypoint_processor_optimized.py`: 기존 글로벌 정규화 구현
- `scripts/compare_normalization_methods.py`: 비교 분석 스크립트

---

## 💡 결론

신체 부위별 정규화는 수어 인식 성능 향상을 위한 **입증된 기법**입니다.

✅ **장점:**

- 손/얼굴 디테일 크게 향상 (33배)
- 학습 효율 개선
- Winston1214 논문에서 +5.9% BLEU 향상 증명

⚠️ **단점:**

- 구현 복잡도 증가
- 데이터 재전처리 필요
- 약간의 처리 시간 증가

**권장 사항:** 소규모 테스트로 효과를 확인한 후, 점진적으로 전체 시스템에 적용하세요!
