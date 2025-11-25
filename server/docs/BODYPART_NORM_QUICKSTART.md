# 신체 부위별 정규화 빠른 시작 가이드

## 🚀 5분 안에 시작하기

### 1️⃣ 단일 비디오 폴더 처리

```python
from input_keypoint.bodypart_normalization_processor import process_video_with_bodypart_norm

# OpenPose JSON 폴더 → CSV 변환
result = process_video_with_bodypart_norm(
    video_folder_path="Source_data/행복하다/NIA_SL_WORD0001_REAL01_A",
    output_dir="bodypart_norm_output"
)

print(f"✓ 완료: {result['csv_path']}")
```

### 2️⃣ 여러 비디오 일괄 처리

```python
import os
from input_keypoint.bodypart_normalization_processor import BodyPartNormalizationProcessor

processor = BodyPartNormalizationProcessor()

word_folder = "Source_data/행복하다"
for folder_name in os.listdir(word_folder):
    folder_path = os.path.join(word_folder, folder_name)
    if os.path.isdir(folder_path):
        try:
            result = processor.process_single_video_optimized(
                folder_path,
                output_dir="bodypart_norm_output"
            )
            print(f"✓ {folder_name}")
        except Exception as e:
            print(f"✗ {folder_name}: {e}")
```

### 3️⃣ 기존 방식과 비교

```bash
cd /Users/parknohyeon/WorkSpace/Python/KSLT
python scripts/compare_normalization_methods.py
```

결과: `normalization_comparison.png` 파일 생성

---

## 📊 무엇이 개선되나?

| 신체 부위  | 기존 범위 | 개선 후 범위 | 향상 비율  |
| ---------- | --------- | ------------ | ---------- |
| 손 (Left)  | 0.03      | 1.0          | **33배** ↑ |
| 손 (Right) | 0.03      | 1.0          | **33배** ↑ |
| 얼굴       | 0.03      | 1.0          | **33배** ↑ |
| 몸         | 1.0       | 1.0          | 동일       |

**결과:** 손가락의 미세한 움직임이 **33배 더 명확하게** 표현됩니다!

---

## ⚙️ 커스터마이징

```python
processor = BodyPartNormalizationProcessor(
    confidence_threshold=0.3,  # 키포인트 신뢰도 임계값 (낮을수록 느슨)
    bbox_padding=0.1,          # 바운딩 박스 패딩 (클수록 여유 공간)
    enable_multiprocessing=True,  # 병렬 처리
    max_workers=4              # 워커 수
)
```

---

## 🔍 결과 확인

```python
import pandas as pd

# 생성된 CSV 파일 확인
df = pd.read_csv("bodypart_norm_output/NIA_SL_WORD0001_REAL01_A_bodypart_norm.csv")

print(f"Shape: {df.shape}")  # (180, 275) - 180프레임 × (1 + 137×2 특징)
print(df.head())

# 손 영역 추출 (keypoint 95-136)
hand_columns = [col for col in df.columns if any(
    f"keypoint_{i}_" in col for i in range(95, 137)
)]
hand_data = df[hand_columns]
print(f"\n손 특징 범위: {hand_data.min().min():.3f} ~ {hand_data.max().max():.3f}")
```

---

## 🎯 다음 단계

1. **데이터 전처리**: 모든 학습 데이터를 신체 부위별 정규화로 변환
2. **모델 재학습**: `config.yaml`에서 `data_path`를 `bodypart_norm_output`으로 변경
3. **성능 비교**: 기존 모델 vs 새 모델의 정확도 비교

---

## 💡 팁

✅ **추천:**

- 먼저 1~2개 단어로 테스트 후 전체 적용
- `confidence_threshold=0.3`, `bbox_padding=0.1` 권장

⚠️ **주의:**

- 학습과 추론에 **동일한 정규화 방식** 사용 필수
- 기존 데이터로 학습한 모델은 새 데이터와 **호환 불가**

---

## 📚 자세한 내용

전체 문서: [`BODYPART_NORMALIZATION_GUIDE.md`](BODYPART_NORMALIZATION_GUIDE.md)
