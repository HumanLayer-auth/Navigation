# M5-004 · CD workflow와 Playwright E2E 스모크 테스트

- **상태**: Draft
- **마일스톤**: M5 · RAG, 평가, 발표 데모 완성
- **권장 진행**: 5주차 후반
- **컴포넌트**: infra / cd / e2e-testing
- **GitHub**: -
- **선행 이슈**: M1-004, M4-003, M5-003

## 설명

CI가 PR의 코드 품질을 막아준다면, CD는 `main`에 들어간 결과가 데모 가능한 형태로 배포되는지 확인한다.
이 이슈는 CD workflow 작성 위치와 Playwright E2E 테스트 위치를 고정한다.

CD workflow는 `.github/workflows/cd.yml`에 둔다. Playwright 테스트는 frontend/backend 어느 한쪽이 아니라
두 서비스를 모두 띄워 사용자 흐름을 검증하므로 루트 `e2e/`에서 관리한다.

## 작업 내용

### 1. CD workflow 작성 위치

- `.github/workflows/cd.yml`을 만든다.
- trigger는 `main` push 또는 `v*` tag를 기준으로 둔다.
- 필요한 secret은 README 또는 workflow 주석에 정리한다.
- 기존 `.github/workflows/project-automation.yml`은 Projects 보드 자동화 전용이므로 수정하지 않는다.

### 2. Backend build/deploy

- backend는 `api/` 기준으로 Docker image를 빌드한다.
- image tag는 `VERSION.md`의 규칙과 맞춘다.
- container security scan을 실행한다.
- staging 또는 데모 서버에 배포한 뒤 `/health` smoke test를 실행한다.

예상 실행 위치:

```bash
cd api
docker build -t navigation/api:<tag> .
```

### 3. Frontend build/deploy

- frontend는 `client/` 기준으로 Flutter web 또는 APK 산출물을 만든다.
- web 데모를 선택하면 GitHub Pages 또는 staging static hosting에 배포한다.
- APK 데모를 선택하면 build artifact로 업로드한다.

예상 실행 위치:

```bash
cd client
flutter build web
# 또는
flutter build apk
```

### 4. Playwright E2E 테스트

- Playwright 프로젝트는 루트 `e2e/`에 둔다.
- 테스트는 backend API와 frontend web preview가 모두 뜬 뒤 실행한다.
- 최소 smoke 시나리오는 앱 진입, 건물 목록 로딩, 목적지 선택 또는 검색, 경로 표시 확인이다.

예상 실행 위치:

```bash
cd e2e
npm ci
npx playwright install --with-deps
npx playwright test
```

workflow에서는 실행 전 아래 두 서비스를 준비한다.

```bash
cd api
uvicorn app.main:app --host 127.0.0.1 --port 8000

cd client
flutter build web
# build/web을 127.0.0.1:3000에서 serve
```

### 5. 실패 시 진단 자료

- Playwright trace, screenshot, video artifact를 업로드한다.
- backend log와 frontend serve log를 artifact로 남긴다.
- CD 실패가 배포 실패인지 E2E 실패인지 job 이름으로 구분한다.

## 파일 (Files)

```
.github/workflows/cd.yml
api/Dockerfile
client/build/web/              (workflow 산출물, VCS 제외)
e2e/package.json
e2e/playwright.config.ts
e2e/tests/navigation-smoke.spec.ts
```

## 수용 기준

- `main` push 또는 tag 기준으로 CD workflow가 실행된다.
- backend image build와 `/health` smoke test가 통과한다.
- frontend web 또는 APK 산출물이 생성된다.
- Playwright E2E smoke test가 `e2e/`에서 실행된다.
- 실패 시 screenshot/trace/log artifact가 남는다.

## 검증

```bash
cd api
pytest

cd ../client
flutter test
flutter build web

cd ../e2e
npm ci
npx playwright test
```

## 범위 밖

- production 운영 배포
- 앱스토어/TestFlight 정식 배포
- 다중 staging 환경
- 장기 모니터링/알림
