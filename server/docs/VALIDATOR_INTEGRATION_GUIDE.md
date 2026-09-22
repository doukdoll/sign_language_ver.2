# 고급 검증 시스템 통합 가이드

## 개요

이 문서는 `app.py` → `realtime/app_main.py` **로컬 카메라 경로**에 통합된 품질 검증기를 설명합니다. 기본 Flask `ai_server.py`의 WebSocket은 이 품질 점수 조정을 사용하지 않습니다. WebSocket의 입력·세션 검증은 [별도 규약](../../docs/RECOGNITION_PROTOCOL.md)을 참고합니다. 수동 카메라 테스트 도구도 `realtime.validator` 설정을 읽어 이 검증기를 적용하지는 않습니다.

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

**코드가 실제로 읽는 위치: `realtime.validator`**

현재 `config/realtime_config.yaml`은 `validator`를 최상위에 두지만 `app_main.py`는 `realtime` 안에서 조회합니다. 따라서 현재 파일의 최상위 값을 바꿔도 적용되지 않고 코드 기본값(아래 값)을 사용합니다. 사용자 지정 설정을 준비할 때는 다음처럼 중첩해야 합니다. 이 문서 갱신에서는 설정이나 코드를 변경하지 않았습니다.

```yaml
# 고급 검증 설정 (머리 겹침 체크 제외)
realtime:
  validator:
    head_occlusion_threshold: 0.8 # 사용 안 함
    min_hand_movement: 0.01
    max_frame_gap: 10
    min_valid_frames_ratio: 0.3
```

## 검증 메트릭

### 1. 손 움직임 (`left_hand_movement`, `right_hand_movement`)
- 각 손의 중심점을 계산하고 프레임 간 이동 거리를 누적
- `max_hand_movement < min_hand_movement`이면 품질 점수 0.7배
- 이 조건만으로 `is_valid=False`가 되지는 않습니다.

### 2. 유효 프레임 비율 (`valid_ratio`)
- 각 프레임에서 손이 감지된 비율 계산
- `valid_ratio < min_valid_frames_ratio`이면 품질 점수 0.5배, `is_valid=False`

### 3. 연속성 (`max_gap`)
- 손이 감지되지 않은 연속 프레임의 최대 길이
- `max_gap > max_frame_gap`이면 품질 점수 0.8배
- 이 조건만으로 `is_valid=False`가 되지는 않습니다.

### 품질 점수 (`quality_score`)
- 초기값 1.0에서 시작
- 각 문제마다 곱셈으로 감소 (0.5 ~ 0.8배)
- 최종 범위: 0.0 ~ 1.0
- 신뢰도 조정: `adjusted_confidence = confidence * quality_score`

## 실행 방법

`server` 디렉터리 기준이며, 카메라·MediaPipe·GUI 지원 OpenCV 환경이 필요합니다. [설치 범위](../README.md)를 먼저 확인하세요.

### 기본 실행
```bash
source .venv/bin/activate
python app.py
```

### 설정 파일 지정

`app.py`는 `--config` 인자를 처리하지 않습니다. 다른 설정은 함수에 직접 전달합니다.

```bash
python -c "from realtime.app_main import realtime_translation; realtime_translation('config/my_realtime_config.yaml')"
```

## 로그 출력 예시

형식을 설명하는 예시이며 측정 결과가 아닙니다. 실제 품질 점수는 코드의 감점 조건에 따라 결정됩니다.

### 정상 검증 통과
```
INFO - 예측: 서울 (원본: 85.3%, 조정: 85.3%) - 품질: 1.00 - 추론시간: 12.4ms
INFO - ✓ 단어 방출: 서울 (신뢰도: 85.3%, 품질: 1.00)
```

### 손 움직임 부족 (감점만 적용)
```
INFO - 예측: 대전 (원본: 75.2%, 조정: 52.6%) - 품질: 0.70 - 추론시간: 11.8ms
INFO - ✓ 단어 방출: 대전 (신뢰도: 52.6%, 품질: 0.70)
```

### 검증 실패 (유효 프레임 비율 낮음)
```
DEBUG - 유효 프레임 비율 낮음: 25.00% < 30.00%
DEBUG - 윈도우 검증 실패: ['low_valid_frame_ratio'], 품질 점수: 0.50
INFO - 예측: 경주 (원본: 68.4%, 조정: 34.2%) - 품질: 0.50 - 추론시간: 13.1ms
```

## 임계값 튜닝 가이드

실시간 추론 환경에서는 너무 엄격한 임계값이 오히려 성능을 해칠 수 있습니다.
아래는 튜닝 예시이지 정확도가 검증된 권장값은 아닙니다. 앞서 설명한 `realtime.validator` 중첩 위치에 적용해야 합니다.

### 임계값이 너무 엄격한 경우 (경고가 너무 많이 나옴)
```yaml
realtime:
  validator:
    min_hand_movement: 0.005 # 더 낮춤
    max_frame_gap: 15 # 더 관대하게
    min_valid_frames_ratio: 0.2 # 더 낮춤
```

### 임계값이 너무 관대한 경우 (품질이 낮은 인식이 많음)
```yaml
realtime:
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
5. **감지 여부의 한계** - 현재 로컬 경로는 confidence를 제거하고 결측 좌표를 0으로 치환한 뒤 검증합니다. 검증기의 2차원 입력 판정은 NaN 여부를 사용하므로 0으로 채운 결측 손을 유효한 것으로 볼 수 있습니다. 이 점수를 실제 감지 품질이나 정확도로 해석하면 안 됩니다.
6. **방출 기준과 표시값** - 품질 점수는 표시 신뢰도에 곱하지만 세그멘터에는 조정 전 모델 확률을 전달합니다. 검증 실패를 자동 방출 차단으로 해석하면 안 됩니다.

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

