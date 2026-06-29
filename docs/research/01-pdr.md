# 01. PDR (Pedestrian Dead Reckoning, 보행자 추측 항법)

## 개념

GPS 없이 **이전 위치 + 이동량(거리·방향)을 누적**해서 현재 위치를 추정하는 방식.
"몇 걸음, 어느 방향으로 갔는가"를 센서로 측정한다.

```
새 위치 = 이전 위치 + 보폭 × (cos(방향), sin(방향))
```

PDR은 크게 세 부분으로 나뉜다.

1. **걸음 감지 (Step Detection)** — 몇 걸음 걸었는가
2. **보폭 추정 (Stride Length Estimation)** — 한 걸음이 몇 미터인가
3. **방향 추정 (Heading)** — 어느 쪽으로 갔는가 → [02 문서](02-sensor-fusion-heading.md)에서 별도로 다룸

이 문서는 1, 2를 다룬다.

## 1. 걸음 감지 (Step Detection)

걸을 때 가속도계에는 상하 진동이 주기적으로 나타난다. 이 파형의 피크를 세면 걸음 수가 된다.

### 기본 파이프라인

```
가속도 3축 → 합벡터 크기 magnitude = sqrt(ax² + ay² + az²)
          → Low-pass filter (걷기 대역만 남기고 노이즈 제거)
          → Peak detection (임계값 + 최소 간격 조건)
          → step count++
```

### 흔한 함정

- **저가 IMU의 노이즈**로 가짜 피크(false peak)가 생긴다. → 단순 임계값만으로는 부정확.
- **최소 시간 간격(보통 0.25~0.4초)** 제약을 둬서 한 걸음을 두 번 세는 걸 막는다.
- 폰을 드는 자세(손·주머니·통화)에 따라 파형이 달라진다 → 자세별 강건성 필요.
- 실무에서는 단순 peak 대신 **자기상관(autocorrelation)·peak-valley·zero-crossing**을 조합한다.

연구 사례에서 허리 착용 시 약 98%, 주머니 착용 시 약 97% 수준의 거리 추정 정확도가 보고되며,
저가 스마트폰 IMU의 노이즈가 피크 검출 일관성을 떨어뜨리는 것이 핵심 난점으로 지적된다.

## 2. 보폭 추정 (Stride Length Estimation)

가장 단순한 방법은 **고정 보폭**(예: 0.7m)이지만 개인차·속도차로 오차가 크다.

### 방법별 비교

| 방법 | 식/원리 | 특징 |
|---|---|---|
| 고정 보폭 | `L = const` | 가장 단순, 오차 큼 |
| 키 기반 | `L = k × height` | 사용자 키 1회 입력으로 개선 |
| Weinberg 모델 | `L = K × (a_max − a_min)^(1/4)` | 가속도 진폭으로 보폭 추정, 널리 쓰임 |
| Kim 모델 | 평균 가속도 기반 | 구현 단순 |
| 적응형/학습 기반 | 보행 주파수·속도에 따라 동적 | 최신, 정확도 최고 |

2024년 적응형 보폭 모델 연구에서는 평균 절대 오차 **0.64m**(기존 모델 7~8m 대비)와
이동 거리 상대 오차 약 **1%**를 보고했다. 다만 이는 wearable·통제 환경 기준이며,
일반 스마트폰·자유 보행에서는 더 보수적으로 잡아야 한다.

### 이 프로젝트의 현실적 선택

- 1차: **Weinberg 모델 + 사용자 키 입력**으로 시작 (구현 쉽고 검증된 baseline).
- 보폭 오차는 어차피 [지도 매칭(03)](03-map-matching.md)이 상당 부분 흡수하므로,
  PDR 단계에서 완벽을 추구하기보다 **합리적 baseline + Particle Filter 보정** 전략이 효율적이다.

## 3. 누적 오차의 본질

PDR의 근본 한계는 **오차가 누적**된다는 것이다.

```
PDR 단독 오차 ≈ 이동 거리의 5~15%
→ 100m 이동 시 5~15m 어긋남
→ 시간이 길수록, 거리가 멀수록 발산
```

따라서 PDR은 **단독으로 쓰지 않는다.** 반드시 지도 매칭(03)으로 주기적으로 보정해서
오차 누적을 끊어줘야 실용 수준이 된다. 이것이 이 프로젝트의 핵심 설계 사상이다.

## 구현 체크리스트

- [ ] 가속도 magnitude + Low-pass filter 파이프라인
- [ ] Peak detection (임계값 + 최소 간격)
- [ ] 자세(손/주머니) 변화에 대한 강건성 테스트
- [ ] Weinberg 보폭 모델 + 키 입력 UI
- [ ] 걸음/거리 추정 정확도 측정 스크립트 (실제 보행 vs 추정)

## 참고 자료

- [Adaptive Step Frequency Detection and Stride Length Estimation for PDR Based on Wearable Devices (ACM, 2024)](https://dl.acm.org/doi/10.1145/3703935.3704046)
- [Step-Detection and Adaptive Step-Length Estimation for PDR at Various Walking Speeds (Sensors/MDPI)](https://www.mdpi.com/1424-8220/16/9/1423)
- [A Robust Step Detection and Stride Length Estimation for PDR Using a Smartphone (IEEE Xplore)](https://ieeexplore.ieee.org/document/9076683/)
- [Context-assisted personalized pedestrian dead reckoning localization with a smartphone (Taylor & Francis, 2024)](https://www.tandfonline.com/doi/full/10.1080/10095020.2024.2338225)
