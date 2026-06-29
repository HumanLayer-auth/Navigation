# 03. 지도 매칭 (Map Matching with Particle Filter)

> 이 프로젝트의 **핵심 알고리즘이자 차별점**. PDR의 누적 오차를 평면도 제약으로 끊어준다.

## 기본 아이디어

```
PDR 단독        → 오차가 계속 누적 (벽을 통과하는 위치도 계산해버림)
PDR + 평면도    → "물리적으로 불가능한 위치"를 걸러내 보정

핵심 제약: 사람은 벽을 통과할 수 없다.
          층 이동은 계단·엘리베이터에서만 일어난다.
```

이 단순한 물리 제약이 오차를 극적으로 줄인다.

## Particle Filter (입자 필터)

가장 널리 쓰이는 지도 매칭 방법. 위치를 단일 점이 아니라 **수백~수천 개의 후보(particle)**로 표현한다.

각 particle은 상태를 가진다:

```
particle = { x, y, heading, weight }
```

### 동작 사이클

```
1. 초기화 (Initialization)
   - 시작 영역(입구 등)에 particle 수백~수천 개를 흩뿌림

2. 예측 (Prediction) — PDR 한 걸음마다
   - 각 particle을 PDR이 추정한 (보폭, 방향)만큼 이동
   - 보폭·방향에 약간의 랜덤 노이즈를 더해 불확실성 표현

3. 가중치 갱신 (Weighting) — 평면도 제약 적용
   - 이전 위치 → 새 위치 선분이 벽을 통과했다면 weight = 0
   - (있다면) Wi-Fi/문 통과 등 추가 관측으로도 가중치 조정

4. 재추출 (Resampling)
   - weight가 0이거나 낮은 particle 제거
   - 살아남은 particle을 복제해 개수 유지

5. 추정 (Estimation)
   - 살아있는 particle들의 가중 평균 = 현재 위치 추정
   - 분산 = 위치 불확실성(지도에 원으로 표시 가능)
```

복도가 많은 건물에서는 벽 제약이 강해서 particle이 자연스럽게 복도 안으로 **수렴**한다.
넓은 홀·로비에서는 제약이 약해 효과가 줄어든다(한계).

## 효과 (정량)

| 방법 | 오차 |
|---|---|
| PDR 단독 | 이동거리의 5~15% |
| PDR + Particle Filter (평면도) | 복잡한 건물에서 90 percentile 기준 **약 3m** |
| 개선된 PF 기법 (PFMK 등) | 평균 오차 **< 1.5m** |

> "벽 통과 문제(wall-crossing)"를 particle 가중치 0으로 해결하는 것이 정확도 향상의 핵심으로
> 학술 문헌에서 일관되게 보고된다.

## 평면도를 활용하는 3가지 접근

학술적으로 실내 지도 보조 항법은 크게 세 갈래다. 셋을 조합하면 더 강력하다.

1. **벽 제약 기반 확률적 매칭** (Particle Filter) — 본 프로젝트의 주 방법.
2. **위상(topological) 매칭** — 건물을 link-node 그래프로 표현해 경로 위에 위치를 스냅.
   → 경로 안내(목적지까지 최단 경로) 계산에도 그대로 재사용 가능.
3. **방향 보정** — 추정 heading을 건물의 주축 방향(cardinal heading)과 비교해 방향 오차 감소.
   → [02 문서](02-sensor-fusion-heading.md)의 자기 간섭 문제를 평면도로 완화.

## 추가 제약(관측) 아이디어

particle 가중치를 더 똑똑하게 만드는 보조 관측들:

- **문 통과 감지**: 막다른 곳/문 앞에서 멈추는 패턴 → 평면도의 문 위치와 매칭.
- **복도 폭 클램핑(Corridor Constraint)**: 복도 폭이 2m면 좌우 오차를 그 안으로 강제.
- **계단/엘리베이터 + 기압계**: 층 변화 감지 → 다층 매칭(기기 한정, 05 문서).

## 구현 단계 전략

```
1단계: 더미 평면도(직사각형 복도 하나)로 Particle Filter 검증
       - 벽 통과 particle이 실제로 제거되는지 시각화
2단계: 실제 건물 평면도(GeoJSON: 벽/복도/문) 적용
3단계: 보조 관측(문 통과, 복도 클램핑) 추가
4단계: 파라미터 튜닝 (particle 수, 노이즈 분산, resampling 주기)
```

### 성능 고려

- particle 수는 정확도 vs 연산량 트레이드오프. 모바일에서 실시간이려면 수백~1~2천 개가 현실적.
- 벽-선분 교차 판정이 매 step마다 particle 수만큼 일어나므로 **공간 분할(grid/quadtree)**로 가속.
- 상태공간 축소(reduced state space) 기법으로 particle 수를 줄이는 최신 연구도 있음.

## 구현 체크리스트

- [ ] 평면도 → 벽 선분 집합 + 보행가능 영역 자료구조
- [ ] particle 구조체 및 초기 분포 생성
- [ ] PDR 기반 prediction (노이즈 포함)
- [ ] 벽-선분 교차 판정 → weight 0
- [ ] resampling (systematic / low-variance)
- [ ] 가중 평균 위치 + 불확실성 추정
- [ ] 더미 평면도 시각화 테스트 하니스

## 참고 자료

- [Application of particle filters for indoor positioning using floor plans (IEEE Xplore)](https://ieeexplore.ieee.org/document/5653830/)
- [An Indoor Map Matching Algorithm Based on Improved Particle Filter (ResearchGate)](https://www.researchgate.net/publication/367100622_An_Indoor_Map_Matching_Algorithm_Based_on_Improved_Particle_Filter)
- [Floor Map-Aware Particle Filtering Based Indoor Navigation System (ResearchGate)](https://www.researchgate.net/publication/354045622_Floor_Map-Aware_Particle_Filtering_Based_Indoor_Navigation_System)
- [A Novel Smartphone PDR Framework Based on Map-Aided Adaptive Particle Filter with a Reduced State Space (MDPI, 2025)](https://www.mdpi.com/2220-9964/14/12/476)
- [An Indoor Navigation Algorithm Using Multi-Dimensional Euclidean Distance and an Adaptive Particle Filter (PMC)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8707401/)
