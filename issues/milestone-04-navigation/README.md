# Milestone 4 · 지도 매칭과 실시간 내비게이션 (Map Matching & Live Navigation)

**권장 진행 주차: 4주차**

M4는 프로젝트의 핵심 차별점인 **실외에서 실내로 전환하고, PDR 오차를 평면도 제약으로 보정하며,
목적지까지 실시간으로 안내하는 경험**을 만드는 마일스톤이다.

이 단계가 끝나면 RAG 없이도 경진대회 핵심 시연인 "입구 진입 → 실내 지도 전환 → 현재 위치 추적 →
경로 표시"가 가능해야 한다.

## 목표 (Definition of Done)

- GPS 입구 반경과 accuracy 변화를 이용해 실내 전환을 감지한다.
- 전환 시 입구 좌표와 heading으로 PDR/PF 초기 위치를 설정한다.
- Particle Filter가 벽 통과 particle을 제거하고 현재 위치와 불확실성을 추정한다.
- 지도 화면에서 현재 위치, 불확실성 원, 목적지 경로가 함께 갱신된다.

## 이슈 목록

| ID | 주차 내 위치 | 컴포넌트 | 상태 | GitHub | 제목 |
|---|---|---|---|---|---|
| M4-001 | 4주차 초반 | navigation / sensors | Draft | - | [실내-실외 자동 전환 baseline](M4-001-indoor-outdoor-transition.md) |
| M4-002 | 4주차 중반 | pdr / routing | Draft | - | [Particle Filter 지도 매칭 baseline](M4-002-particle-filter-map-matching.md) |
| M4-003 | 4주차 후반 | client / navigation | Draft | - | [실시간 경로 안내와 이탈 처리](M4-003-live-navigation-reroute.md) |

## 진행 순서

```text
M3 PDR 결과 + M2 평면도 데이터
   ├─> M4-001 (실내 전환 초기화)
   ├─> M4-002 (Particle Filter 보정)
   └─> M4-003 (실시간 내비게이션 UI)
```

M4-001과 M4-002는 병렬 검토가 가능하지만, M4-003은 둘의 결과를 화면에서 합치는 작업이다.

## 범위 밖

- 자연어 목적지 검색
- 정량 평가 리포트 완성
- 발표 영상 제작
- 다층 자동 전환 고도화
