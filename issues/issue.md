# ISSUE

Navigation 프로젝트의 **마일스톤별 GitHub 이슈 초안과 설명**을 모아두는 문서다.
실제 GitHub 이슈를 만들기 전에, 어떤 마일스톤에 어떤 작업을 넣을지와 그 이유를 이 파일에서 먼저 정리한다.

> 작성 규칙
> - 마일스톤 단위로 섹션을 나눈다.
> - 상세 이슈 식별자는 `M1-001`, `M2-001`처럼 마일스톤 단위 번호를 사용한다.
> - 상태는 `Draft`, `Ready`, `Created`, `Done` 중 하나로 기록한다.
> - GitHub 이슈로 생성한 뒤에는 `GitHub` 칸에 이슈 번호를 적는다.
> - 각 이슈의 `설명`은 GitHub 이슈 본문에 그대로 옮길 수 있게 작성한다.

## 요약 표

> 이후 마일스톤은 디렉토리 단위로 나누고 `M1-NNN`처럼 **마일스톤마다 001부터** 매긴다.

## 주차별 운영안

마일스톤은 너무 많이 쪼개지 않기 위해 **1주차 = 1마일스톤** 기준으로 잡는다.
각 마일스톤은 3개 이슈 안팎으로 제한하고, 한 주 안에서 "초반/중반/후반" 순서로 진행한다.

| 주차 | 마일스톤 | 목표 | 핵심 결과물 |
|---|---|---|---|
| 1주차 | M1 · 프로젝트 초기 설정 | Flutter + FastAPI 골격과 통신 확인 | 앱/서버 실행, `/buildings` 연동, CI 기본 게이트 |
| 2주차 | M2 · 실내 지도 데이터와 기본 경로 | 정적 평면도와 POI 경로 표시 | GeoJSON 스키마, 지도 렌더링, 최단 경로 |
| 3주차 | M3 · 센서 수집과 PDR 기본 동작 | 센서 입력으로 PDR 위치 추정 | 권한/센서 점검, 걸음/보폭, heading/PDR |
| 4주차 | M4 · 지도 매칭과 실시간 내비게이션 | 실내 전환 + Particle Filter + 실시간 안내 | 자동 전환, 보정 위치, 이탈/도착 처리 |
| 5주차 | M5 · RAG, 평가, 발표 데모 완성 | 자연어 UX와 발표용 근거 정리 | RAG 목적지, CDF 평가, 데모 패키지, CD 배포 |

## CI/CD 배치 원칙

이 저장소의 실제 서비스 디렉토리는 `client/`와 `api/`다.
문서에서 frontend는 `client/`, backend는 `api/`로 본다.

| 구분 | 작성 위치 | 담당 이슈 | 실행 위치 |
|---|---|---|---|
| CI workflow | `.github/workflows/ci.yml` | M1-004 | PR/push마다 static analysis, unit, integration |
| CD workflow | `.github/workflows/cd.yml` | M5-004 | `main` 머지 또는 태그 기준 Docker build/push, staging deploy, smoke |
| Frontend unit/widget test | `client/test/` | M1-001, M1-004 | `cd client && flutter test test/` |
| Frontend integration test | `client/integration_test/` | M1-003, M1-004 | `cd client && flutter test integration_test/` |
| Backend unit test | `api/tests/unit/` | M1-002, M1-004 | `cd api && pytest tests/unit` |
| Backend integration test | `api/tests/integration/` | M1-003, M1-004 | `cd api && pytest tests/integration` |
| Playwright E2E test | `e2e/` | M5-004 | CD 또는 별도 E2E job에서 backend와 frontend web 서버를 띄운 뒤 `cd e2e && npx playwright test` |

Playwright는 프론트엔드 또는 백엔드 한쪽의 단위 테스트가 아니라 두 서비스를 실제 사용자 흐름으로
검증하는 E2E 테스트이므로 루트의 `e2e/`에서 관리한다.

## 마일스톤 디렉토리

상세 이슈는 마일스톤별 디렉토리에서 파일 단위로 관리한다.

| 마일스톤 | 권장 주차 | 디렉토리 | 이슈 | 내용 |
|---|---|---|---|---|
| M1 | 1주차 | [milestone-01-setup/](milestone-01-setup/) | M1-001~004 | Flutter·FastAPI 골격 생성, 연동, CI 기본 게이트 |

M2 이후 상세 이슈 디렉토리는 현재 유지하지 않는다.

## 우선순위 메모

- M1~M4가 프로젝트의 핵심 시연 경로다.
- 시간이 부족하면 M5-001(RAG)은 aliases 기반 검색으로 축소하고, M5-002(평가)와 M5-003(데모 패키지)을 우선한다.
- 각 마일스톤은 한 주 안에 끝내는 것을 기준으로 하지만, 센서/PDR 튜닝은 M4~M5에서 반복될 수 있다.

---

## 새 이슈 작성 템플릿

```markdown
# M0-000 · 제목

- **상태**: Draft
- **마일스톤**: M0 · 마일스톤 이름
- **권장 진행**: N주차 초반/중반/후반
- **컴포넌트**: client / api / routing / data / demo / infra / docs / planning
- **GitHub**: -
- **선행 이슈**: 없음

## 설명

이 이슈가 왜 필요한지, 어떤 마일스톤 목표와 연결되는지 적는다.

## 작업 내용

- 구현하거나 정리할 작업을 적는다.

## 수용 기준

- 완료 여부를 판단할 수 있는 조건을 적는다.
```
