# Git Convention

> 최종 수정: 2026-09-22
>
> 작성자: 황순철

이 문서는 프로젝트의 브랜치, 커밋, Pull Request 규칙을 정의한다.

---

## 1. 브랜치 생성

- 형식: `{담당}-{작업유형}/{짧은설명}`
- 담당 영역:
  - `be`: Backend
  - `fe`: Frontend
  - `ai`: AI Server
  - `hw`: Hardware
  - `de`: Deployment
- 작업 유형:
  - `feature`: 새로운 기능
  - `fix`: 버그 수정
  - `refactor`: 코드 구조 개선
  - `docs`: 문서 작성 및 수정
  - `test`: 테스트 작성 및 수정
  - `chore`: 설정, 의존성 등 기타 작업
- 짧은 설명은 영문 kebab-case 사용을 권장한다.
- 기능 개발은 `develop`에서 분기하고, 배포 작업은 필요에 따라 `main` 또는 `develop`에서 분기한다.

예시:

```text
be-feature/booking-api
fe-fix/camera-permission
ai-refactor/inference-pipeline
de-docs/docker-guide
```

## 2. 커밋 메시지

- 형식: `[{담당}-{작업유형}] {요약}`
- 요약은 변경 내용을 알 수 있도록 간결하게 작성한다.
- 하나의 커밋에는 하나의 논리적인 변경만 포함한다.

예시:

```text
[be-feature] 예매 생성 API 구현
[fe-fix] 카메라 권한 오류 수정
[ai-refactor] 추론 전처리 로직 분리
[de-docs] Docker 실행 가이드 작성
```

## 3. Pull Request

- 작업 브랜치를 원격 저장소에 push한 뒤 `develop`을 대상으로 Pull Request를 생성한다.
- 제목 형식: `[{담당}-{작업유형}] {제목}`
- 본문에는 작업 내용, 테스트 결과, 참고 사항을 작성한다.
- 병합 전 Files changed에서 의도하지 않은 변경이 포함되지 않았는지 직접 확인한다.
- 병합 전 `Frontend`, `Backend`, `AI session tests` CI 체크의 성공을 확인한다. 검사 범위와 필수 상태 검사 설정은 [CI 문서](docs/CI.md)를 참고한다.

예시:

```text
[fe-feature] 실시간 수어 인식 화면 구현
```

## 4. 병합

- 기능 브랜치는 `develop`으로 병합한다.
- 병합 방식은 **Squash and merge**를 사용해 작업 내역을 하나의 커밋으로 정리한다.
- 병합이 끝나면 작업 브랜치를 삭제한다.
- 모든 수정 Pull Request의 대상 브랜치는 `develop`으로 지정한다.
- `main` 비교 및 반영은 저장소 소유자가 직접 진행한다. 에이전트는 `main` 대상 Pull Request 생성이나 병합을 수행하지 않는다.

## 5. 기본 작업 흐름

```text
develop
  └─ 작업 브랜치 생성
       └─ 작업 및 커밋
            └─ 원격 저장소에 push
                 └─ Pull Request 생성
                      └─ 변경 사항 확인
                           └─ Squash and merge
                                └─ 작업 브랜치 삭제
```
