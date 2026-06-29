# Milestone 3 · 센서 수집과 PDR 기본 동작 (Sensors & PDR)

**권장 진행 주차: 3주차**

M3는 정적 지도 데모를 실제 보행 추정으로 연결하는 단계다.
스마트폰 센서 capability를 확인하고, 걸음 감지, 보폭 추정, 방향 추정, PDR 엔진을 최소 형태로
구현한다.

이 마일스톤의 목표는 완벽한 정확도가 아니라, "기록된 센서 또는 실기기 센서 입력으로 위치 추정값이
연속적으로 나온다"는 것을 확인하는 것이다. 지도 제약 보정은 M4에서 붙인다.

## 목표 (Definition of Done)

- 앱 시작 시 센서 지원 여부와 권한 상태를 확인한다.
- 가속도 기반 걸음 감지와 보폭 추정이 동작한다.
- 자이로/지자기 기반 heading 추정값을 PDR 엔진에 연결한다.
- 센서 로그 또는 mock stream으로 PDR 경로를 재현할 수 있다.

## 이슈 목록

| ID | 주차 내 위치 | 컴포넌트 | 상태 | GitHub | 제목 |
|---|---|---|---|---|---|
| M3-001 | 3주차 초반 | client / sensors | Draft | - | [센서 capability 점검과 권한 플로우](M3-001-sensor-capability-permissions.md) |
| M3-002 | 3주차 중반 | pdr | Draft | - | [걸음 감지와 보폭 추정 baseline](M3-002-step-detection-stride-baseline.md) |
| M3-003 | 3주차 후반 | pdr / navigation | Draft | - | [Heading 추정과 PDR 엔진 통합](M3-003-heading-pdr-engine.md) |

## 진행 순서

```text
M3-001 (센서/권한)
   └─> M3-002 (걸음/보폭)
          └─> M3-003 (heading + PDR 통합)
```

## 범위 밖

- Particle Filter 지도 매칭
- 자동 실내 전환
- 경로 안내 재탐색
- RAG

## 주차 운영 메모

센서 알고리즘은 기기와 자세에 따라 흔들리므로, 3주차에는 "실시간으로 값이 나온다"와
"로그로 재현 가능하다"를 우선한다. 정확도 튜닝은 M4와 M5 평가에서 반복한다.
