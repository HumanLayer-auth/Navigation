# 05. 기기 센서 호환성 (Device & Sensor Compatibility)

> PDR은 센서가 있어야 동작한다. **자이로 유무가 사실상 지원 가능 여부를 가른다.**

## 필요한 센서와 역할

| 센서 | PDR에서의 역할 | 없으면 |
|---|---|---|
| 가속도계 (Accelerometer) | 걸음 감지 | PDR 불가 (거의 모든 폰에 있음) |
| 자이로스코프 (Gyroscope) | 방향(회전) 추적 | 방향 오차 급증 → 사실상 PDR 불가 |
| 지자기 (Magnetometer) | 절대 방위·드리프트 보정 | 방향 누적 오차 보정 약화 |
| 기압계 (Barometer) | 층 변화 감지 | 다층 자동 구분 불가 (2D만) |

## 센서 탑재 현황 (요약)

### 아이폰 (iPhone)

- **자이로스코프**: iPhone 4부터 전 모델 탑재.
- **기압계**: iPhone 6부터 탑재.
- 모션 코프로세서가 가속도·자이로·지자기·기압계 융합을 처리해 PDR + 지도매칭에 유리.

| 모델 | 가속도 | 자이로 | 지자기 | 기압계 | PDR | 층 감지 |
|---|---|---|---|---|---|---|
| iPhone 6 이상 | O | O | O | O | O | O |
| iPhone SE (1세대, 2016) | O | O | O | X | O | X |
| iPhone SE (2세대~) | O | O | O | O | O | O |

→ **SE 1세대 제외 사실상 전 모델 풀 지원.**

### 삼성 갤럭시 (Samsung Galaxy)

- **S 시리즈(플래그십)**: S4부터 현재까지 기압계 포함 전 센서 탑재 → 전 모델 풀 지원.
  (갤럭시 S III가 초기 기압계 탑재 모델 중 하나)
- **A 시리즈(중급/보급)**: 모델별 편차 큼.
  - 상위(A3x/A5x/A7x): 대체로 자이로·지자기 O, 기압계는 모델 따라 다름.
  - 하위(A0x/A1x): **자이로·기압계 미탑재 사례 많음.** 예) A15 5G는 기압계 없음.

| 라인 | 가속도 | 자이로 | 지자기 | 기압계 | PDR | 비고 |
|---|---|---|---|---|---|---|
| Galaxy S4 이상 | O | O | O | O | O | 풀 지원 |
| Galaxy A 상위 (A3x↑) | O | O | O | △ | O | 기압계 확인 필요 |
| Galaxy A 하위 (A0x~A1x) | O | △/X | O | X | △/X | 자이로 없으면 PDR 불가 |

> 위 표는 사전조사 기반 일반화다. **실제 타겟 기기는 출시 스펙 시트로 개별 확인**해야 하며,
> 같은 모델명도 지역·세대에 따라 센서가 다를 수 있다.

## 최소 사양 결정 (권장)

```
필수 (Required):   가속도계 + 자이로 + 지자기   → PDR + 방향 추적
권장 (Recommended): + 기압계                    → 층 자동 감지

→ "자이로 미탑재 기기는 미지원"으로 명시하는 것이 현실적.
```

## 런타임 센서 체크 & Graceful Degradation

앱 실행 시 센서 보유 여부를 확인하고 없으면 우아하게 기능을 낮춘다.

```
앱 시작
 → 센서 capability 점검 (가속도/자이로/지자기/기압계)
 → 자이로 없음   → "이 기기는 정밀 실내 측위를 지원하지 않습니다" 안내 + 제한 모드
 → 기압계 없음   → 다층 자동 구분 비활성, 층 수동 선택 UI 제공
 → 전부 있음     → 풀 기능
```

- Flutter에서는 `sensors_plus`의 스트림 구독 가능 여부 / 플랫폼 채널로 센서 존재를 확인한다.
  (안드로이드 `SensorManager.getDefaultSensor()`에 해당하는 동작)

## 경진대회 관점 메모

- 데모·발표는 **풀 지원 기기(아이폰/갤럭시 S)** 로 진행해 정확도를 최대한 보여준다.
- 호환성 표와 graceful degradation은 "현실적 한계를 인지하고 설계했다"는 **엔지니어링 성숙도**로
  심사에서 가점 요소가 된다. 한계를 숨기지 말고 명시적으로 다루는 게 유리하다.

## 구현 체크리스트

- [ ] 타겟 데모 기기 2~3종의 실제 센서 스펙 확정
- [ ] 런타임 센서 capability 점검 모듈
- [ ] 자이로/기압계 부재 시 폴백 UI·메시지
- [ ] 최소 사양을 README/발표자료에 명시

## 참고 자료

- [Survey of smartphone-based datasets for indoor localization (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2542660525002665)
- [Floor positioning method indoors with smartphone's barometer (Taylor & Francis)](https://www.tandfonline.com/doi/full/10.1080/10095020.2019.1631573)
- [Using smartphone pressure sensors to measure vertical velocities of elevators, stairways (arXiv)](https://arxiv.org/pdf/1607.00363)
