# 04. 실내-실외 자동 전환 (Seamless Indoor-Outdoor Transition)

> "그냥 걸어 들어가면 자동으로 실내 지도로 바뀐다" — 이 프로젝트의 시연 임팩트 포인트.

## 풀어야 할 두 문제

1. **언제 전환할 것인가** (Transition Detection): 사용자가 실내로 들어온 순간을 어떻게 아는가.
2. **어디서부터 시작할 것인가** (Initialization): 실내 모드로 바뀔 때 PDR의 초기 위치를 무엇으로 잡는가.

전환 지점(건물 입구)은 GPS가 불안정하고 신호가 끊기기 시작하는 **가장 까다로운 구간**이다.
핸드오버 전략이 전체 추적 품질을 좌우한다.

## 전환 감지 방법 비교

| 방법 | 신호 | 장점 | 단점 |
|---|---|---|---|
| **GPS 입구 좌표 매칭** | 입구 반경 진입 | 구현 쉬움, 안정적 | 입구 좌표 사전 등록 필요 |
| **GPS accuracy 급락** | `accuracy` 값 급등 | 추가 데이터 불필요 | 지하주차장·터널과 혼동 |
| GPS C/N0 (신호대잡음비) | 위성 신호 품질 저하 | 민감하게 감지 | 원시 GNSS 접근 필요 |
| Wi-Fi SSID 등장 | 건물 AP 감지 | 명확한 실내 신호 | 건물별 AP 사전 등록 |
| 기압계 변화 | 문 여닫을 때 미세 변화 | 보조 신호 | 단독으론 불안정 |
| 조도/소리/활동 | 빛·잔향·걸음 패턴 | ML로 95% 수준 달성 사례 | 구현 복잡 |

학술 문헌은 단일 신호보다 **다중 신호 융합 + 저전력 상시 감지 → 모호할 때만 GNSS 호출**
구조를 권장한다. 소리(잔향) 기반은 약 95%, ML 기반 IO 판별도 높은 정확도가 보고된다.

## 이 프로젝트의 권장 조합

복잡한 ML 없이 경진대회에서 안정적으로 동작하는 **2신호 조합**:

```
주 신호:  GPS 위치가 건물 입구 좌표 반경(5~10m) 안에 들어옴
보조 신호: GPS accuracy 값이 급격히 악화 (실내 진입 징후)

→ 두 조건이 함께/연속으로 만족되면 "실내 진입" 확정
```

지하주차장 오탐 문제는 "**등록된 건물 입구 근처에서만** accuracy 급락을 실내 신호로 해석"하는
방식으로 상당 부분 회피된다(입구 좌표가 게이트 역할).

## 전환 시 초기 위치 확정

PDR은 시작점을 스스로 모른다. 자동 전환의 핵심 이득이 바로 **시작점을 자동으로 준다**는 것.

```
실내 진입 감지
    ↓
진입 직전 GPS 궤적의 진행 방향 + 입구 좌표
    ↓
입구 좌표를 PDR 시작점으로 설정
진입 방향을 초기 heading으로 설정
    ↓
Particle Filter 초기 분포를 입구 주변에 생성
    ↓
실내 PDR + 지도 매칭 시작
```

- 입구를 통과하는 방향은 보통 정해져 있어(문은 한 방향으로 들어감) **초기 heading의 좋은 단서**가 된다.
- particle을 입구 주변에 약간의 분산으로 뿌리면, 걸으면서 복도 제약으로 빠르게 수렴한다.

## 역방향 전환 (실내 → 실외)

- 출구 근처에서 GPS accuracy가 회복되면 다시 야외 GPS 모드로 핸드오버.
- 1차 데모에서는 "들어가는 방향"만 확실히 보여줘도 충분. 나가는 전환은 선택 구현.

## 데이터 요구사항

백엔드 건물 데이터에 **입구(entrance) 좌표 목록**이 필요하다(06 문서 데이터 구조와 연결).

```
building:
  id, name
  entrances:
    - { lat, lng, floor, heading_hint }   # heading_hint: 입구 통과 방향
```

## 구현 체크리스트

- [ ] geolocator로 야외 GPS 추적 + accuracy 스트림 수집
- [ ] 입구 좌표 반경 진입 판정(geofence 유사)
- [ ] accuracy 급락 감지 로직 + 입구 게이트 조건
- [ ] 전환 시 입구 좌표·방향 → PDR/PF 초기화 연결
- [ ] 전환 지연·오탐 측정 (입구 진입 후 몇 초/오탐률)

## 참고 자료

- [Seamless Indoor–Outdoor Localization Through Transition Detection (Electronics/MDPI, 2025)](https://www.mdpi.com/2079-9292/14/13/2598)
- [A Fast Indoor/Outdoor Transition Detection Algorithm Based on Machine Learning (Sensors/MDPI)](https://www.mdpi.com/1424-8220/19/4/786)
- [A GPS Sensing Strategy for Accurate and Energy-Efficient Outdoor-to-Indoor Handover (ResearchGate)](https://www.researchgate.net/publication/262155885_A_GPS_Sensing_Strategy_for_Accurate_and_Energy-Efficient_Outdoor-to-Indoor_Handover_in_Seamless_Localization_Systems)
- [Mobile User Indoor-Outdoor Detection through Physical Daily Activities (Sensors/MDPI)](https://www.mdpi.com/1424-8220/19/3/511)
