# M1-004 · CI workflow와 테스트 디렉토리 기준 수립

- **상태**: Draft
- **마일스톤**: M1 · 프로젝트 초기 설정
- **권장 진행**: 1주차 후반
- **컴포넌트**: infra / ci / testing
- **GitHub**: -
- **선행 이슈**: M1-001, M1-002, M1-003

## 설명

프론트엔드와 백엔드 골격이 생긴 뒤에는 PR마다 같은 검증이 자동으로 돌아야 한다.
이 이슈는 GitHub Actions CI workflow 위치와 frontend/backend 테스트 디렉토리 기준을 고정한다.

이 저장소에서 frontend는 `client/`, backend는 `api/`다. workflow 파일은 서비스 디렉토리 안이 아니라
저장소 공통 자동화 위치인 `.github/workflows/ci.yml`에 둔다.

## 작업 내용

### 1. CI workflow 작성 위치

- `.github/workflows/ci.yml`을 만든다.
- trigger는 `pull_request`, `push`를 기본으로 둔다.
- 기존 `.github/workflows/project-automation.yml`은 Projects 자동화 전용이므로 CI workflow와 섞지 않는다.
- Flutter, Python 의존성 cache를 설정한다.

### 2. Frontend 테스트 위치

- frontend 코드는 `client/`에서 검증한다.
- unit/widget test는 `client/test/`에 둔다.
- app-level integration test는 `client/integration_test/`에 둔다.
- CI 명령은 아래 기준을 따른다.

```bash
cd client
flutter pub get
flutter analyze
flutter test test/
flutter test integration_test/
```

### 3. Backend 테스트 위치

- backend 코드는 `api/`에서 검증한다.
- 순수 service/domain/repository unit test는 `api/tests/unit/`에 둔다.
- FastAPI TestClient, 실제 라우터, 테스트 repository를 묶는 integration test는 `api/tests/integration/`에 둔다.
- CI 명령은 아래 기준을 따른다.

```bash
cd api
pip install -r requirements.txt
pytest tests/unit
pytest tests/integration
```

### 4. Playwright 위치는 CD/E2E 이슈로 분리

- Playwright는 frontend/backend 단위 테스트가 아니라 전체 사용자 흐름 E2E 테스트다.
- 테스트 파일은 루트 `e2e/`에서 관리한다.
- 실제 실행 workflow는 M5-004의 `.github/workflows/cd.yml` 또는 별도 `e2e` job에서 다룬다.

### 5. 보안/정적 분석 확장 자리

- Python static analysis는 이후 `ruff`/`black --check`를 추가할 수 있게 job을 분리한다.
- Flutter static analysis는 `flutter analyze`를 기본 gate로 둔다.
- dependency/security scan은 별도 job으로 추가할 수 있게 주석 또는 TODO를 남긴다.

## 파일 (Files)

```
.github/workflows/ci.yml
client/test/
client/integration_test/
api/tests/unit/
api/tests/integration/
```

## 수용 기준

- PR 또는 push 시 `.github/workflows/ci.yml`이 실행된다.
- frontend unit/widget test가 `client/test/`에서 실행된다.
- frontend integration test가 `client/integration_test/`에서 실행된다.
- backend unit test가 `api/tests/unit/`에서 실행된다.
- backend integration test가 `api/tests/integration/`에서 실행된다.
- 기존 Projects 자동화 workflow와 CI workflow의 책임이 분리되어 있다.

## 검증

```bash
cd client
flutter analyze
flutter test test/
flutter test integration_test/

cd ../api
pytest tests/unit
pytest tests/integration
```

GitHub Actions에서는 PR을 열어 `ci.yml` job들이 같은 명령을 실행하는지 확인한다.

## 범위 밖

- Docker image build/push
- staging 배포
- Playwright E2E 전체 시나리오
- production release
