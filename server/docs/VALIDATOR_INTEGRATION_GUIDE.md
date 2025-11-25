# 고급 검증 시스템 통합 가이드

## 개요

`advanced_validators.py`의 검증 알고리즘이 실시간 추론 시스템에 통합되었습니다.
머리 겹침 체크는 제외되고, 다음 3가지 검증 기능이 적용됩니다:

1. **손 움직임 체크** - 최소 손 이동 거리 확인
2. **유효 프레임 비율 체크** - 손이 감지된 프레임 비율 확인
3. **연속성 체크** - 손 추적이 불연속적이지 않은지 확인

## 변경 사항

### 1. `input_keypoint/advanced_validators.py`

**변경 내용:**
- `validate_sequence()` 메서드에 `skip_head_occlusion` 매개변수 추가
- `skip_head_occlusion=True`로 설정하면 머리 겹침 체크를 건너뜀

**사용 예시:**
```python
from input_keypoint.advanced_validators import AdvancedHandValidator

validator = AdvancedHandValidator(
    min_hand_movement=0.01,
    max_frame_gap=10,
    min_valid_frames_ratio=0.3
)

# 머리 겹침 체크 제외
result = validator.validate_sequence(keypoints_sequence, skip_head_occlusion=True)
```

### 2. `realtime/app_main.py`

**변경 내용:**
- `AdvancedHandValidator` import 추가
- 검증기 초기화 (설정 파일에서 매개변수 로드)
- 슬라이딩 윈도우 추론 전 검증 수행
- 검증 결과를 신뢰도에 반영
- 검증 실패 시 경고 로그 출력

**통합 흐름:**
```
1. 슬라이딩 윈도우 데이터 준비 (WIN, 274)
2. 274차원 → (WIN, 137, 2) 형태로 변환
3. 검증 수행 (skip_head_occlusion=True)
4. 모델 추론 수행
5. 신뢰도 조정: adjusted_confidence = confidence * quality_score
6. 검증 실패 시 경고 로그와 함께 방출
```

### 3. 설정 파일

**`config/realtime_config.yaml`:**
```yaml
# 고급 검증 설정 (머리 겹침 체크 제외)
validator:
  head_occlusion_threshold: 0.8 # 머리 위 손 비율 임계값 (사용 안 함)
  min_hand_movement: 0.01 # 최소 손 이동 거리 (실시간용 낮은 임계값)
  max_frame_gap: 10 # 최대 프레임 간격 (연속성 체크, 실시간용 관대한 값)
  min_valid_frames_ratio: 0.3 # 최소 유효 프레임 비율 (실시간용 낮은 비율)
```

## 검증 메트릭

### 1. 손 움직임 (`left_hand_movement`, `right_hand_movement`)
- 각 손의 중심점을 계산하고 프레임 간 이동 거리를 누적
- `max_hand_movement < min_hand_movement`이면 품질 점수 0.7배

### 2. 유효 프레임 비율 (`valid_ratio`)
- 각 프레임에서 손이 감지된 비율 계산
- `valid_ratio < min_valid_frames_ratio`이면 품질 점수 0.5배, `is_valid=False`

### 3. 연속성 (`max_gap`)
- 손이 감지되지 않은 연속 프레임의 최대 길이
- `max_gap > max_frame_gap`이면 품질 점수 0.8배

### 품질 점수 (`quality_score`)
- 초기값 1.0에서 시작
- 각 문제마다 곱셈으로 감소 (0.5 ~ 0.8배)
- 최종 범위: 0.0 ~ 1.0
- 신뢰도 조정: `adjusted_confidence = confidence * quality_score`

## 실행 방법

### 기본 실행
```bash
source .venv/bin/activate
python app.py
```

### 설정 파일 지정
```bash
source .venv/bin/activate
python app.py --config config/realtime_config.yaml
```

## 로그 출력 예시

### 정상 검증 통과
```
INFO - 예측: 서울역 (원본: 85.3%, 조정: 81.1%) - 품질: 0.95 - 추론시간: 12.4ms
INFO - ✓ 단어 방출: 서울역 (신뢰도: 81.1%, 품질: 0.95)
```

### 검증 실패 (낮은 품질)
```
DEBUG - 윈도우 검증 실패: ['insufficient_hand_movement'], 품질 점수: 0.70
INFO - 예측: 대전 (원본: 75.2%, 조정: 52.6%) - 품질: 0.70 - 추론시간: 11.8ms
WARNING - ⚠ 낮은 품질 단어 방출: 대전 (신뢰도: 52.6%, 품질: 0.70) - 이슈: ['insufficient_hand_movement']
```

### 검증 실패 (유효 프레임 비율 낮음)
```
DEBUG - 유효 프레임 비율 낮음: 25.00% < 30.00%
DEBUG - 윈도우 검증 실패: ['low_valid_frame_ratio'], 품질 점수: 0.50
INFO - 예측: 경주 (원본: 68.4%, 조정: 34.2%) - 품질: 0.50 - 추론시간: 13.1ms
```

## 임계값 튜닝 가이드

실시간 추론 환경에서는 너무 엄격한 임계값이 오히려 성능을 해칠 수 있습니다.
현재 설정은 실시간용으로 조정된 값입니다.

### 임계값이 너무 엄격한 경우 (경고가 너무 많이 나옴)
```yaml
validator:
  min_hand_movement: 0.005 # 더 낮춤
  max_frame_gap: 15 # 더 관대하게
  min_valid_frames_ratio: 0.2 # 더 낮춤
```

### 임계값이 너무 관대한 경우 (품질이 낮은 인식이 많음)
```yaml
validator:
  min_hand_movement: 0.02 # 더 높임
  max_frame_gap: 5 # 더 엄격하게
  min_valid_frames_ratio: 0.5 # 더 높임
```

## 주의사항

1. **머리 겹침 체크는 제외됨** - `skip_head_occlusion=True`로 설정되어 있습니다.
2. **실시간 성능** - 검증 로직은 매우 가볍지만, 로그 레벨을 DEBUG로 설정하면 성능에 영향을 줄 수 있습니다.
3. **품질 점수 반영** - 검증 실패 시에도 단어는 방출되지만, 낮은 신뢰도로 표시됩니다.
4. **로그 확인** - `logs/kslt.log` 파일에서 자세한 검증 정보를 확인할 수 있습니다.

## 검증 비활성화 방법

검증 기능을 완전히 비활성화하려면 `realtime/app_main.py`에서 다음과 같이 수정:

```python
# 검증 로직 비활성화 (주석 처리)
# validation_result = validator.validate_sequence(keypoints_for_validation, skip_head_occlusion=True)

# 대신 기본 결과 사용
validation_result = {
    'is_valid': True,
    'quality_score': 1.0,
    'issues': []
}
```

## 문제 해결

### 검증 관련 에러 발생 시
1. 로그 레벨을 DEBUG로 설정하여 자세한 정보 확인
2. validator 설정이 config 파일에 올바르게 추가되었는지 확인
3. numpy 버전 확인 (requirements.txt 참고)

### 성능 저하 발생 시
1. 로그 레벨을 INFO 또는 WARNING으로 상향 조정
2. validator 임계값을 더 관대하게 설정
3. 검증 로직 비활성화 고려

## 추가 개선 사항 (향후)

1. **적응형 임계값** - FPS와 연동하여 동적으로 임계값 조정
2. **통계 누적** - 세션 전체의 검증 통계 수집 및 보고
3. **시각화** - 화면에 품질 점수를 시각적으로 표시
4. **필터링 옵션** - 낮은 품질 단어를 방출하지 않는 옵션 추가

