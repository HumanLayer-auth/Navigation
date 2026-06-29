# 08. 평가 방법과 데모 설계 (Evaluation & Demo)

심사위원에게 "정말 동작한다 + 얼마나 정확한가"를 정량·정성으로 보여주기 위한 평가 설계.

## 표준 평가 지표

실내 측위 분야에는 확립된 지표가 있다. 이를 쓰면 발표 신뢰도가 올라간다.

| 지표 | 의미 | 비고 |
|---|---|---|
| **위치 오차 (point error)** | 추정 위치와 실제 위치의 거리(m) | 가장 기본 |
| **CEP / CE50** | 오차의 50% 분위(중앙값) | Circular Error Probable |
| **CE95** | 오차의 95% 분위 | 최악 근처 보장 수준 |
| **CDF** | 오차 분포 누적함수 | 측위 성능의 표준 표현 |
| **RMSE** | 오차 제곱평균제곱근 | 통계적 정확도 |
| **floor detection rate** | 층 인식 정확도 | 다층 구현 시 |

> **EvAAL/IPIN 경진대회**에서는 CDF의 **75% 지점**을 핵심 지표로 권장한다. 우리도
> "CE75 = N m" 형태로 보고하면 학술적으로 인정되는 표현이 된다. CE50/CE95도 함께 제시.

## 측정 방법 (Ground Truth 확보)

오차를 재려면 **실제 위치(ground truth)** 가 필요하다. 경진대회 규모에서 현실적인 방법:

```
방법 A) 바닥에 기준점 마킹
  - 복도 바닥에 테이프로 알려진 좌표 점들을 표시
  - 그 점들을 정확히 밟고 지나가며 추정 위치 기록 → 오차 계산

방법 B) 정해진 경로 왕복
  - 시작→목적지 정해진 경로를 걷고, 끝점에서의 위치 오차(closure error) 측정
  - 왕복 후 출발점 복귀 오차로 누적 오차 평가

방법 C) 체크포인트 통과 시각 기록
  - 알려진 지점(문, 코너) 통과 순간 타임스탬프 → 그 시점 추정 위치와 비교
```

## 비교 실험 설계 (차별점 증명)

핵심 메시지("지도 매칭이 오차를 줄인다")를 **A/B로 증명**한다.

| 조건 | 설명 | 기대 |
|---|---|---|
| Baseline | PDR 단독 (지도 매칭 끔) | 오차 누적, 벽 통과 |
| Ours | PDR + Particle Filter | 오차 1~3m로 수렴 |

→ 같은 경로를 두 조건으로 그려 **CDF 곡선 2개를 겹쳐 보여주면** 차이가 한눈에 보인다.
이 그래프 하나가 발표의 핵심 슬라이드가 된다.

추가 비교축(여유 있으면):

- 자이로 only vs 자이로+지자기 융합 (heading 정확도)
- 고정 보폭 vs Weinberg 보폭
- 자동 전환 지연·오탐률

## 데모 시나리오 (시연 대본)

```
1. [야외] 건물 밖에서 앱 실행 → 지도에 GPS 위치
2. [전환] 입구로 걸어 들어감 → 화면이 자동으로 실내 평면도로 전환 (임팩트!)
3. [추적] 복도를 걸으며 마커가 실시간으로 따라옴, 불확실성 원이 좁혀짐
4. [길찾기] 목적지(예: 화장실/매장) 선택 → 평면도 위에 경로 표시
5. [정확도] 미리 측정한 CDF 그래프로 "PDR 단독 vs Ours" 비교 제시
```

- 시연은 **풀 지원 기기(아이폰/갤럭시 S)** 로, **복도가 많은 환경**(매칭 효과 큰 곳)에서.
- 실패 대비: 라이브 시연 실패에 대비해 **사전 녹화 영상 + 측정 데이터**를 백업으로 준비.

## 평가 일정 제안

```
프로토타입 동작 →
  1) 단위 정확도 측정 (걸음 수, 거리, heading 각각)
  2) 통합 경로 측정 (CDF, CE50/75/95)
  3) A/B 비교 (Baseline vs Ours)
  4) 결과를 00 문서 "성공 기준" 표에 실측치로 갱신
```

## 심사 어필 포인트 정리

| 축 | 어필 |
|---|---|
| 기술 난도 | 센서 융합 + Particle Filter 직접 구현 |
| 차별성 | 인프라 0, 평면도만으로 동작 ([07](07-related-work.md)) |
| 완성도 | 자동 전환으로 끊김 없는 UX ([04](04-indoor-outdoor-transition.md)) |
| 정량성 | 표준 지표(CDF/CE75) + A/B 비교 그래프 |
| 성숙도 | 기기 호환성·한계를 명시적으로 다룸 ([05](05-device-sensor-compatibility.md)) |

## 구현 체크리스트

- [ ] ground truth 측정 프로토콜 확정(방법 A/B/C 중)
- [ ] 추정 위치 로깅 + 오차 계산 스크립트
- [ ] CDF/CE50/75/95 산출 및 그래프화
- [ ] Baseline vs Ours A/B 실험
- [ ] 데모 대본 + 백업 영상/데이터

## 참고 자료

- [A Testing and Evaluation Framework for Indoor Navigation and Positioning Systems (Sensors/MDPI, 2025)](https://www.mdpi.com/1424-8220/25/7/2330)
- [Off-line Evaluation of Indoor Positioning Systems: IPIN 2020 Competition (ResearchGate)](https://www.researchgate.net/publication/351826977_Off-line_Evaluation_of_Indoor_Positioning_Systems_in_Different_Scenarios_The_Experiences_from_IPIN_2020_Competition)
- [Evaluating Ambient Assisted Living Solutions: The Localization Competition / EvAAL (ResearchGate)](https://www.researchgate.net/publication/260721486_Evaluating_Ambient_Assisted_Living_Solutions_The_Localization_Competition)
- [Evaluation of Indoor Localisation Systems: ISO/IEC 18305 (ResearchGate)](https://www.researchgate.net/publication/328981367_Evaluation_of_Indoor_Localisation_Systems_Comments_on_the_ISOIEC_18305_Standard)
