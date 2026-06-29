# Milestone 5 · RAG, 평가, 발표 데모 완성 (Demo, RAG & Evaluation)

**권장 진행 주차: 5주차**

M5는 경진대회 제출물을 완성하는 마일스톤이다.
기본 내비게이션이 동작한 뒤 자연어 목적지 검색을 붙이고, 정확도 평가 자료와 발표용 백업 자료를
준비한다.

RAG는 차별화 기능이지만, 측위가 흔들리면 우선순위를 낮출 수 있다. 이 마일스톤의 최우선은
작동하는 데모와 정량 근거다.

## 목표 (Definition of Done)

- 자연어로 목적지를 입력하면 POI 후보 또는 목적지가 반환된다.
- PDR 단독과 Particle Filter 보정 결과를 비교할 수 있는 로그/그래프가 있다.
- 발표 시연 대본, fallback 영상/스크린샷, 실행 체크리스트가 준비된다.
- `.github/workflows/cd.yml`에서 데모 배포, Docker build/push, smoke test 위치가 정리된다.
- README와 문서가 실제 실행 상태를 설명한다.

## 이슈 목록

| ID | 주차 내 위치 | 컴포넌트 | 상태 | GitHub | 제목 |
|---|---|---|---|---|---|
| M5-001 | 5주차 초반 | api / rag / client | Draft | - | [자연어 목적지 파싱 RAG baseline](M5-001-rag-destination-baseline.md) |
| M5-002 | 5주차 중반 | evaluation / demo | Draft | - | [측위 평가 로그와 CDF 리포트](M5-002-evaluation-logging-cdf.md) |
| M5-003 | 5주차 후반 | demo / docs | Draft | - | [경진대회 데모 패키지와 발표 체크리스트](M5-003-competition-demo-package.md) |
| M5-004 | 5주차 후반 | infra / cd / e2e-testing | Draft | - | [CD workflow와 Playwright E2E 스모크 테스트](M5-004-cd-playwright-workflow.md) |

## 진행 순서

```text
M5-001 (RAG 목적지 UX)      선택 기능, 시간 부족 시 축소 가능
M5-002 (정량 평가 자료)    발표 신뢰도 핵심
M5-003 (데모 패키지)       제출/시연 안정성 핵심
M5-004 (CD/E2E)             main 머지 후 데모 배포 안정성 확인
```

M5-002와 M5-003은 반드시 끝내고, M5-001은 측위 데모 안정성이 확보된 범위 안에서 진행한다.
M5-004는 배포 대상이 확정된 뒤 작성하되, Playwright E2E 테스트 위치는 이 이슈에서 먼저 고정한다.

## 범위 밖

- 상용 수준 배포
- 다건물 운영
- 장기 백그라운드 추적 최적화
- 실시간 서버 운영 자동화
