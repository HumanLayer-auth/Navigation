# 02. 센서 융합과 방향 추정 (Sensor Fusion & Heading)

## 왜 방향이 가장 어려운가

PDR에서 **거리보다 방향(heading) 오차가 위치를 더 크게 망친다.**
방향이 몇 도만 틀어져도 멀리 갈수록 위치가 부채꼴로 벌어지기 때문이다.

문제는 방향을 측정하는 두 센서가 각각 결함이 있다는 점이다.

| 센서 | 측정 | 장점 | 치명적 약점 |
|---|---|---|---|
| 자이로스코프 (Gyroscope) | 각속도 → 적분해 회전각 | 단기적으로 매우 정확, 빠름 | **드리프트** — 적분 오차가 시간에 따라 누적 |
| 지자기 센서 (Magnetometer) | 지구 자기장 → 절대 방위 | 장기적으로 북쪽 고정, 누적 없음 | **자기 간섭** — 철골·전자기기·엘리베이터에 취약 |

즉 자이로는 "단기 정확·장기 발산", 지자기는 "장기 안정·단기 노이즈". **둘은 상호 보완적**이다.
그래서 둘(+가속도계)을 융합한다.

## IMU와 AHRS

- **IMU (Inertial Measurement Unit)**: 가속도계 + 자이로 (+ 때로 지자기).
- **AHRS (Attitude and Heading Reference System)**: IMU 데이터를 융합해 **자세(roll/pitch/yaw)와
  방위(heading)**를 산출하는 시스템. 대부분의 스마트폰 "방향" API가 내부적으로 AHRS를 쓴다.

핵심은 **3종 센서 융합**:

```
가속도계 → 중력 방향(roll, pitch) 기준 제공
자이로   → 빠른 회전 변화 추적 (단기)
지자기   → 절대 북쪽 기준 제공 (장기 드리프트 보정)
        ↓
    Sensor Fusion → 안정적인 heading
```

## 융합 필터 비교

### 1. Complementary Filter (상보 필터)

가장 단순하고 가볍다. 자이로의 고주파(단기)와 가속도/지자기의 저주파(장기)를 가중 합산.

```
angle = α × (angle + gyro × dt) + (1 − α) × (accel/mag 추정각)
        └ 자이로(단기) ┘          └ 가속도·지자기(장기 보정) ┘
```

- 장점: 연산 가벼움, 이해·구현 쉬움 → 모바일·프로토타입에 적합.
- 단점: 정밀도는 Kalman/Madgwick보다 낮음.

### 2. Madgwick Filter

쿼터니언(quaternion) 표현 + 경사하강법(gradient descent)으로 자이로 측정 오차를 보정.
가속도/지자기로 자이로 드리프트를 잡는 **상보 필터 계열**이지만 더 정교하다.

- 자이로 = 단기 변화, 가속도·지자기 = 장기 보정이라는 원리는 같음.
- IMU(가속도+자이로) 버전과 MARG(+지자기) 버전이 있음.
- 임베디드·모바일에서 널리 채택. 짐벌락 없는 쿼터니언이라 안정적.

### 3. Mahony Filter

비례-적분(PI) 제어 기반. Madgwick과 함께 가장 널리 쓰이는 AHRS.

### 4. (Extended) Kalman Filter

이론적으로 최적에 가깝지만 튜닝·연산 부담이 큼. 경진대회 규모에선 과할 수 있음.

### 선택 가이드

| 상황 | 추천 |
|---|---|
| 빠른 프로토타입, 가벼움 우선 | **Complementary Filter** |
| 정확도·완성도 어필 | **Madgwick** (또는 Mahony) |
| 플랫폼 기본 제공 활용 | 모바일 OS의 rotation vector / fused orientation |

> **현실적 권장**: 1차는 플랫폼 제공 방향값 또는 Complementary로 빠르게 동작시키고,
> 정확도가 부족하면 Madgwick으로 교체. 핵심은 어떤 필터든 **지도 매칭(03)이 방향 오차도
> 함께 보정**한다는 점이라 필터 선택에 과투자하지 않는 것.

## 자기 간섭(magnetic disturbance) 대응

실내 철골·엘리베이터·전자기기 근처에서 지자기는 크게 틀어진다.

- 자기장 크기가 정상 범위(약 25~65µT)를 벗어나면 **그 순간 지자기 보정 가중치를 낮춘다.**
- 간섭 구간에서는 자이로에 더 의존하고, 안정 구간에서 다시 지자기로 드리프트를 잡는다.
- 평면도가 있으면 **복도 방향(건물 cardinal heading)과 비교**해 방향 오차를 추가로 줄일 수 있다 → 03 문서.

## 구현 체크리스트

- [ ] 플랫폼 fused orientation vs 자체 필터 비교 측정
- [ ] Complementary Filter baseline 구현
- [ ] (선택) Madgwick으로 업그레이드, 정확도 비교
- [ ] 자기 간섭 감지 → 지자기 가중치 동적 조정
- [ ] heading 드리프트 측정(제자리 회전 후 복귀 오차)

## 참고 자료

- [Madgwick Orientation Filter — AHRS documentation](https://ahrs.readthedocs.io/en/latest/filters/madgwick.html)
- [Comparison of AHRS using foot-mounted MIMU: basic, Madgwick, and Mahony (ResearchGate)](https://www.researchgate.net/publication/324048187_Comparison_of_attitude_and_heading_reference_systems_using_foot_mounted_MIMU_sensor_data_basic_Madgwick_and_Mahony)
- [Madgwick & Kalman Filter for Sensor Fusion Explained (QSense)](https://qsense-motion.com/qsense-imu-motion-sensor/madgwick-filter-sensor-fusion/)
- [Smartphone MEMS Accelerometer and Gyroscope Measurement Errors (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC10490716/)
