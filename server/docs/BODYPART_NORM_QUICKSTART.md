# 신체 부위별 정규화 빠른 시작

이 가이드는 `BodyPartNormalizationProcessor`로 **이미 추출된 OpenPose JSON**을 CSV로 변환하는 방법입니다. 원본 영상에서 키포인트를 추출하는 도구가 아니며, 예시 데이터 경로는 저장소에 포함되어 있지 않습니다. 명령과 Python 코드는 `server` 디렉터리 기준입니다.

## 단일 시퀀스 변환

입력 폴더에는 `sample_000001_keypoints.json`처럼 끝에서 두 번째 `_` 구간이 프레임 번호인 파일이 있어야 합니다. JSON의 `people[0]`에 Pose 25개·Face 70개·양손 각 21개의 x, y, confidence 값이 필요합니다.

```python
from input_keypoint.bodypart_normalization_processor import process_video_with_bodypart_norm

result = process_video_with_bodypart_norm(
    video_folder_path="path/to/openpose_sequence",  # 실제 입력 폴더로 교체
    output_dir="bodypart_norm_output",
    target_frames=180,
    confidence_threshold=0.3,
    bbox_padding=0.1,
    enable_multiprocessing=False,
)
print(result["csv_path"])
```

이 프로세서는 numpy, pandas, scipy를 사용합니다. 서비스 스모크 전용 의존성에는 scipy가 없으므로 전처리 실행 환경을 별도로 준비해야 합니다.

## 결과 확인

```python
import pandas as pd

df = pd.read_csv(result["csv_path"])
print(df.shape)  # 기본 target_frames에서 (180, 275)
features = df.drop(columns="frame").to_numpy()
print(features.shape)  # (180, 274)
```

출력 이름은 `<입력 폴더명>_bodypart_norm.csv`이며, 첫 열은 1부터 시작하는 `frame`, 나머지는 `keypoint_0_x`부터 `keypoint_136_y`까지입니다. `enable_multiprocessing`이라는 옵션 이름과 달리 현재 병렬 구현은 `ThreadPoolExecutor`입니다.

## 적용 전에 확인할 것

- 학습과 추론의 키포인트 순서, 좌표 단위, 정규화, 결측 처리, 시간축 보정이 같아야 합니다.
- 이 프로세서는 기본 180프레임 **선형 보간**을 수행합니다. Flask WebSocket은 **128프레임 수집 후 180까지 0 padding**을 사용하므로 동일한 시간축 정책이 아닙니다.
- 이전 가이드의 `scripts/compare_normalization_methods.py`와 완성된 학습 `config.yaml`은 현재 저장소에 없습니다.
- 좌표 범위 확장은 인식 정확도 향상을 증명하지 않습니다. 과거 예시의 `33배` 수치는 현재 데이터로 재측정한 결과가 아닙니다.

구현과 제한 사항은 [상세 가이드](BODYPART_NORMALIZATION_GUIDE.md), 서비스 입력은 [서버 README](../README.md)를 참고합니다.
