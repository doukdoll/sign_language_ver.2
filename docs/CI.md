# 자동 검증 (GitHub Actions)

워크플로: [ci.yml](../.github/workflows/ci.yml)

## 실행 시점

- `develop` 대상 PR 생성·재개·추가 커밋 시 실행합니다.
- `develop`에 push되면 병합 결과를 다시 검사합니다.
- `main` push나 `main` 대상 PR은 실행 대상이 아닙니다. 배포·자동 병합 기능은 없습니다.
- 파일 경로 필터 없이 세 작업을 병렬 실행합니다. 문서만 바꾼 PR도 동일하게 검사합니다.
- 같은 PR/브랜치에 새 실행이 생기면 진행 중인 이전 실행을 취소합니다.

## 검사 범위

| 체크 이름 | 환경 | 검사 |
| --- | --- | --- |
| `Frontend` | Ubuntu 24.04, Node.js 24 | `npm ci`, lint(경고도 실패), 세션·카메라 생명주기·예약 테스트, TypeScript 검사·Vite 빌드 |
| `Backend` | Ubuntu 24.04, Temurin Java 17, Gradle 8.14.4 | `clean build`로 전체 테스트 및 JAR 생성 |
| `AI session tests` | Ubuntu 24.04, Python 3.10 | 표준 라이브러리 세션 검사와 Flask HTTP 경계 검사, 실제 모델 없이 실행 |

백엔드 WebSocket 테스트는 임의 로컬 포트의 모의 AI 서버를 사용하고 HTTP 테스트는 요청/응답을 모의 처리합니다. 예매 조회는 H2 저장소 테스트도 수행합니다. 별도 MySQL, Python 서버, API 키는 필요하지 않습니다.

AI 세션 검사는 `python -S`로 site-packages 로딩을 제외합니다. 별도 HTTP 검사는 `server/requirements-test.txt`의 Flask와 그 의존성만 설치하고 테스트 클라이언트에 전처리·추론 함수를 주입합니다. 체크 이름은 기존 `AI session tests`를 유지합니다. 전체 `requirements.txt` 설치, 실제 모델 추론, 학습, 정확도 측정은 수행하지 않습니다. 카메라·MediaPipe·ONNX 전체 연결 검증은 [실시간 검증 절차](LIVE_RECOGNITION_CHECK.md)로 별도 수행합니다.

현재 저장소에 `gradle-wrapper.jar`가 없어 CI는 Gradle 8.14.4를 설치한 후 `gradle` 명령을 사용합니다. Gradle 버전 변경 시 `backend/gradle/wrapper/gradle-wrapper.properties`와 워크플로의 `gradle-version`을 함께 갱신해야 합니다.

## 실패 확인과 로컬 재현

PR의 Checks 또는 저장소 Actions의 `CI` 실행에서 실패한 작업과 단계를 확인합니다. 백엔드 테스트 보고서는 성공·실패 시 `backend-test-reports` 아티팩트로 7일 보관합니다(실행 취소 또는 보고서 생성 전 실패는 제외).

저장소 루트에서 각 블록을 별도로 실행합니다. Windows에서는 설치 환경에 따라 `npm.cmd`, `gradle.bat`, Python 실행 파일의 절대 경로를 사용합니다.

```bash
cd frontend
npm ci
npm run lint -- --max-warnings 0
npm test
npm run build
```

```bash
cd backend
gradle --no-daemon --console=plain clean build
```

```bash
cd server
python -S -m unittest tests.test_sessions -v
python -m pip install -r requirements-test.txt
python -m unittest tests.test_http_api -v
```

`npm run build`에 타입 검사가 포함되어 있습니다. 현재 Vite의 번들 크기 경고는 빌드를 실패시키지 않습니다. 이 CI는 별도 보안 취약점 스캔을 포함하지 않습니다.

## 권한과 유지 관리

- GitHub 토큰은 `contents: read`로 제한하고 checkout 인증 정보를 남기지 않습니다. 별도 secret은 사용하지 않습니다.
- 액션은 확인한 릴리스의 전체 커밋 SHA로 고정하며, 옆 주석에 버전을 기록합니다. 갱신 시 공식 릴리스와 SHA를 함께 확인합니다.
- npm 캐시는 잠금 파일을 기준으로 사용합니다. Gradle은 basic 캐시를 사용하며 `develop` 실행에서만 캐시를 씁니다.
- 이 파일 추가만으로 실패한 PR의 병합이 강제 차단되지는 않습니다. `develop` 보호 규칙에서 위 세 체크를 필수 상태 검사로 지정해야 합니다. CI 구성·문서 현행화 작업에서는 저장소 보호 규칙을 변경하지 않았습니다.

공식 설정 참고: [setup-node](https://github.com/actions/setup-node), [setup-gradle](https://github.com/gradle/actions/blob/main/docs/setup-gradle.md), [setup-python](https://github.com/actions/setup-python).

## 초기 CI 구성 검증 기록 (2026-09-22, PR #18)

- `actionlint 1.7.12`: 워크플로 문법·표현식 검사 통과.
- Windows 로컬에서 Node.js 24로 `npm ci` 후 lint(오류·경고 0개), 세션 테스트 8개, 타입 검사 및 프로덕션 빌드 통과. 기존 번들 크기·브라우저 호환성 데이터 갱신 경고는 남아 있습니다.
- Java 17 / Gradle 8.14.4의 `clean build`: 테스트 16개 통과, JAR 생성 성공.
- Python 3.10의 `python -S -m unittest tests.test_sessions -v`: 테스트 15개 통과.
- `npm ci`의 감사 요약에서 기존 의존성 취약점 19개(low 1, moderate 4, high 14)가 보고됐습니다. 자동 수정이나 의존성 변경은 하지 않았습니다.

GitHub-hosted Ubuntu runner에서도 다음 실행을 확인했습니다. 두 실행 모두 `Frontend`, `Backend`, `AI session tests`가 성공했습니다.

- [PR #18 CI, run #1](https://github.com/doukdoll/sign_language_ver.2/actions/runs/35729782219): 커밋 `ffc19f4`, `pull_request` 이벤트.
- [develop 병합 후 CI](https://github.com/doukdoll/sign_language_ver.2/actions/runs/35732788235): squash 커밋 `439741d`, `push` 이벤트.

로컬 검사·GitHub CI·실제 모델/카메라 검증은 서로 다른 범위입니다. 위 성공 기록은 이후 모든 커밋의 통과를 보장하지 않으며, 새 PR의 Checks를 다시 확인해야 합니다.

## 코드 정리 검증 기록 (2026-09-22)

`de-refactor/code-quality-cleanup`에서 다음 로컬 검증을 통과했습니다.

- FE: 최종 잠금 파일로 `npm ci`, lint 오류·경고 0개, 타입 검사·프로덕션 빌드, 테스트 34개(세션 8 / 모의 카메라 11 / 예약·조회 15).
- BE: `clean build`, 테스트 26개. 별도 `clean test bootJar` 실행에서는 Dockerfile과 같은 단일 실행 JAR 생성도 확인했습니다.
- AI: 표준 라이브러리 세션 테스트 15개와 Flask HTTP 테스트 15개, 합계 30개. HTTP 테스트는 모델·NumPy·카메라 모듈 없이 실행합니다.
- `actionlint 1.7.12`와 Markdown 상대 링크·JSON 예제 검사 통과.
- 실제 BE·Python·ONNX 합성 입력 연결 재검증 통과([상세 범위](LIVE_RECOGNITION_CHECK.md)).

위 내용은 2026-09-22 PR 생성 전의 로컬 검증 기록입니다. 이후 2026-09-23 [PR #20](https://github.com/doukdoll/sign_language_ver.2/pull/20)을 `develop` 대상으로 생성했습니다. 해당 PR의 Checks에서 최종 커밋의 `Frontend`, `Backend`, `AI session tests` 결과를 확인합니다. 작업 브랜치 push만으로는 워크플로가 실행되지 않으며, PR 생성 이후에는 추가 커밋도 검사합니다.

- [PR #20 최초 CI](https://github.com/doukdoll/sign_language_ver.2/actions/runs/35800861860): 코드 정리 커밋 `9ac2634`에서 세 작업 모두 성공했습니다. 이후 문서 보완 커밋도 병합 전에 다시 검사합니다.

기존 번들 크기·브라우저 호환성 데이터 경고와 Gradle 9 비호환 기능 경고는 남아 있습니다. 실제 카메라·왕복 UI·Docker 실행·보안 검사는 이번 자동 검증 범위가 아닙니다.
