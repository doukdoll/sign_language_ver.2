# 고급 검증 시스템 통합 - 변경 사항 요약

날짜: 2025-11-11
작업: `advanced_validators.py`의 검증 알고리즘 통합 (머리 겹침 체크 제외)

## 변경된 파일

### 1. `input_keypoint/advanced_validators.py`
**변경 내용:**
- `validate_sequence()` 메서드에 `skip_head_occlusion` 매개변수 추가
- `skip_head_occlusion=True`로 설정하면 머리 겹침 체크를 건너뜀
- 나머지 검증 기능은 그대로 유지:
  - 손 움직임 체크
  - 유효 프레임 비율 체크
  - 연속성 체크

### 2. `realtime/app_main.py`
**변경 내용:**
- `AdvancedHandValidator` import 추가
- 검증기 초기화 코드 추가 (147-154 라인)
  - 설정 파일에서 validator 설정 로드
  - 실시간용 임계값 적용 (기본값)
- 슬라이딩 윈도우 추론 전 검증 로직 추가 (259-267 라인)
  - 274차원 벡터를 (WIN, 137, 2) 형태로 변환
  - 검증 수행 (머리 겹침 체크 제외)
  - 검증 실패 시 DEBUG 로그 출력
- 신뢰도 조정 로직 추가 (287-294 라인)
  - `adjusted_confidence = confidence * quality_score`
  - 화면 표시용 변수에 조정된 신뢰도 사용
- 로그 출력 강화 (296-306 라인)
  - 원본 신뢰도와 조정된 신뢰도 모두 표시
  - 품질 점수 표시
- 단어 방출 로직 수정 (318-336 라인)
  - 검증 통과 시: 일반 방출
  - 검증 실패 시: 경고와 함께 방출 (사용자가 판단할 수 있도록)

### 3. `config/realtime_config.yaml`
**추가 내용:**
- `validator` 섹션 추가 (41-46 라인)
  ```yaml
  validator:
    head_occlusion_threshold: 0.8
    min_hand_movement: 0.01
    max_frame_gap: 10
    min_valid_frames_ratio: 0.3
  ```

### 4. `config/test_config.yaml`
**추가 내용:**
- `realtime.validator` 섹션 추가 (36-41 라인)
  - realtime_config.yaml과 동일한 설정

### 5. `docs/VALIDATOR_INTEGRATION_GUIDE.md` (신규)
**내용:**
- 검증 시스템 통합 가이드
- 변경 사항 상세 설명
- 검증 메트릭 설명
- 실행 방법 및 로그 출력 예시
- 임계값 튜닝 가이드
- 문제 해결 방법

### 6. `README.md`
**변경 내용:**
- 주요 특징 섹션 업데이트 (17-20 라인)
  - 고급 검증 시스템 설명 추가
  - 머리 겹침 체크 제외 명시
- 고급 검증 시스템 섹션 추가 (66-100 라인)
  - 검증 항목 설명
  - 설정 방법
  - 로그 출력 예시
  - 가이드 문서 링크

### 7. `CHANGES.md` (신규)
**내용:**
- 변경 사항 요약 문서 (이 파일)

## 통합된 검증 기능

### 1. 손 움직임 체크
- 각 손의 중심점 계산
- 프레임 간 이동 거리 누적
- `max_hand_movement < min_hand_movement` 시 품질 점수 0.7배

### 2. 유효 프레임 비율 체크
- 각 프레임에서 손 감지 여부 확인
- 유효 프레임 비율 계산
- `valid_ratio < min_valid_frames_ratio` 시 품질 점수 0.5배, `is_valid=False`

### 3. 연속성 체크
- 손이 감지되지 않은 연속 프레임의 최대 길이 계산
- `max_gap > max_frame_gap` 시 품질 점수 0.8배

## 제외된 기능

### 머리 겹침 체크
- `check_head_occlusion()` 메서드는 남아있지만 실시간 추론에서는 사용하지 않음
- `skip_head_occlusion=True`로 설정하여 건너뜀
- 향후 필요 시 `skip_head_occlusion=False`로 변경하여 활성화 가능

## 실행 방법

### 기본 실행
```bash
source .venv/bin/activate
python app.py
```

### 검증 로그 확인
```bash
# 로그 레벨을 DEBUG로 설정하여 상세 정보 확인
tail -f logs/kslt.log | grep "검증"
```

## 예상 로그 출력

### 정상 검증 통과
```
2025-11-11 16:30:45 - kslt.realtime - INFO - 예측: 서울역 (원본: 85.3%, 조정: 81.1%) - 품질: 0.95 - 추론시간: 12.4ms
2025-11-11 16:30:45 - kslt.realtime - INFO - ✓ 단어 방출: 서울역 (신뢰도: 81.1%, 품질: 0.95)
```

### 검증 실패 (손 움직임 부족)
```
2025-11-11 16:30:48 - kslt.realtime - DEBUG - 손 움직임 부족: 0.005 < 0.01
2025-11-11 16:30:48 - kslt.realtime - DEBUG - 윈도우 검증 실패: ['insufficient_hand_movement'], 품질 점수: 0.70
2025-11-11 16:30:48 - kslt.realtime - INFO - 예측: 대전 (원본: 75.2%, 조정: 52.6%) - 품질: 0.70 - 추론시간: 11.8ms
2025-11-11 16:30:48 - kslt.realtime - WARNING - ⚠ 낮은 품질 단어 방출: 대전 (신뢰도: 52.6%, 품질: 0.70) - 이슈: ['insufficient_hand_movement']
```

### 검증 실패 (유효 프레임 비율 낮음)
```
2025-11-11 16:30:51 - kslt.realtime - DEBUG - 유효 프레임 비율 낮음: 25.00% < 30.00%
2025-11-11 16:30:51 - kslt.realtime - DEBUG - 윈도우 검증 실패: ['low_valid_frame_ratio'], 품질 점수: 0.50
2025-11-11 16:30:51 - kslt.realtime - INFO - 예측: 경주 (원본: 68.4%, 조정: 34.2%) - 품질: 0.50 - 추론시간: 13.1ms
```

## 성능 영향

### 추가 연산
- 검증 로직은 매우 가볍습니다 (< 1ms)
- 실시간 추론 성능에 거의 영향 없음
- 로그 레벨을 DEBUG로 설정하면 로그 I/O로 인해 약간의 성능 저하 가능

### 메모리 사용
- 검증기 인스턴스: 무시할 수 있는 수준
- 검증 결과 딕셔너리: 각 프레임당 < 1KB

## 향후 개선 사항

1. **적응형 임계값**
   - FPS와 연동하여 동적으로 임계값 조정
   - 현재는 고정 임계값 사용

2. **통계 누적**
   - 세션 전체의 검증 통계 수집
   - 평균 품질 점수, 실패 비율 등 보고

3. **시각화**
   - 화면에 품질 점수를 시각적으로 표시
   - 진행 바 또는 색상 코딩

4. **필터링 옵션**
   - 낮은 품질 단어를 방출하지 않는 옵션 추가
   - 최소 품질 임계값 설정

## 테스트 체크리스트

- [x] `advanced_validators.py` 수정
- [x] `app_main.py`에 검증 로직 통합
- [x] 설정 파일에 validator 섹션 추가
- [x] 문서화 완료
- [ ] 실제 카메라로 실시간 추론 테스트
- [ ] 다양한 임계값 조합 테스트
- [ ] 로그 출력 확인

## 주의사항

1. **실시간 환경에 최적화된 임계값**
   - 기본 임계값은 실시간 환경에 맞게 관대하게 설정됨
   - 오프라인 배치 처리 시에는 더 엄격한 임계값 권장

2. **검증 실패 시에도 단어 방출**
   - 검증 실패 시에도 단어는 방출됨 (낮은 신뢰도로)
   - 사용자가 최종 판단할 수 있도록 정보 제공

3. **로그 레벨 주의**
   - DEBUG 레벨: 모든 검증 정보 출력 (성능 약간 저하 가능)
   - INFO 레벨: 방출된 단어와 기본 정보만 출력 (권장)
   - WARNING 레벨: 낮은 품질 경고만 출력

## 참고 문서

- [검증 시스템 통합 가이드](docs/VALIDATOR_INTEGRATION_GUIDE.md)
- [프로젝트 구조 가이드](PROJECT_STRUCTURE.md)
- [README](README.md)

