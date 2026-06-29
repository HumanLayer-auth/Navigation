# CI/CD 이슈 설계

Navigation의 CI/CD 자동화는 GitHub Actions를 기준으로 작성한다.
이 문서는 CI/CD 작업만 따로 보기 위한 요약이며, 실제 마일스톤 이슈는 `issues/` 아래에서 관리한다.

## 현재 workflow 상태

- 기존 `.github/workflows/project-automation.yml`은 GitHub Projects 보드 자동화 전용이다.
- CI/CD와 책임이 다르므로 수정하거나 제거하지 않는다.
- 새 CI는 `.github/workflows/ci.yml`, 새 CD는 `.github/workflows/cd.yml`에 작성한다.

## CI-001 · PR 검증 workflow

- **마일스톤 이슈**: `issues/milestone-01-setup/M1-004-ci-test-workflow.md`
- **목적**: PR/push마다 frontend/backend 정적 분석, unit test, integration test를 실행한다.
- **관련 파일**
  - `.github/workflows/ci.yml`
  - `client/test/`
  - `client/integration_test/`
  - `api/tests/unit/`
  - `api/tests/integration/`
- **수용 기준**
  - `client/`에서 `flutter analyze`, `flutter test test/`, `flutter test integration_test/`가 실행된다.
  - `api/`에서 `pytest tests/unit`, `pytest tests/integration`이 실행된다.
  - Flutter pub cache와 Python package cache를 사용한다.
  - static analysis 실패 시 PR을 막는다.
- **검증 방법**
  - PR을 열어 CI job이 통과하는지 확인한다.

## CI-002 · 보안/정적 분석 확장

- **마일스톤 이슈**: M1-004에 TODO로 남기고, 필요 시 별도 이슈로 분리한다.
- **목적**: dependency/security scan과 lint/format gate를 추가한다.
- **관련 파일**
  - `.github/workflows/ci.yml`
  - `api/requirements.txt`
  - `client/pubspec.yaml`
- **수용 기준**
  - backend dependency scan이 실행된다.
  - frontend dependency audit 또는 Flutter 분석이 실행된다.
  - 실패 시 PR을 막는다.
- **검증 방법**
  - 취약 의존성 또는 lint 실패를 넣었을 때 CI가 실패하는지 확인한다.

## CD-001 · Docker build/push와 staging 배포

- **마일스톤 이슈**: `issues/milestone-05-demo-rag/M5-004-cd-playwright-workflow.md`
- **목적**: `main` merge 또는 tag 기준으로 backend image를 만들고 staging/demo 환경에 배포한다.
- **관련 파일**
  - `.github/workflows/cd.yml`
  - `api/Dockerfile`
  - `VERSION.md`
- **수용 기준**
  - `api/`에서 Docker image가 빌드된다.
  - Docker Buildx layer cache를 사용한다.
  - container security scan이 실행된다.
  - 배포 후 `/health` smoke test가 통과한다.
- **검증 방법**
  - `main` push 또는 tag로 CD를 실행하고 smoke test 결과를 확인한다.

## CD-002 · Frontend 산출물과 Playwright E2E

- **마일스톤 이슈**: `issues/milestone-05-demo-rag/M5-004-cd-playwright-workflow.md`
- **목적**: frontend web/APK 산출물을 만들고 전체 사용자 흐름을 Playwright로 확인한다.
- **관련 파일**
  - `.github/workflows/cd.yml`
  - `client/`
  - `e2e/package.json`
  - `e2e/playwright.config.ts`
  - `e2e/tests/navigation-smoke.spec.ts`
- **수용 기준**
  - `client/`에서 `flutter build web` 또는 `flutter build apk`가 실행된다.
  - backend와 frontend preview를 띄운 뒤 `e2e/`에서 `npx playwright test`가 실행된다.
  - 실패 시 trace, screenshot, log artifact가 업로드된다.
- **검증 방법**
  - 로컬 또는 GitHub Actions에서 Playwright smoke test를 실행한다.
