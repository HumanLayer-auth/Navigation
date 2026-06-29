# Navigation 사전조사 노트

최종 갱신일: 2026-06-29

> **주제 확정(2026-06-29)**: 기존 노트의 "보행 약자 접근성 경로 추천" 방향에서,
> **GPS 없이 스마트폰 센서만으로 동작하는 Map-Aided PDR 기반 실내 내비게이션**으로 전환했다.
> 야외→실내 자동 전환을 핵심 경험으로 한다. 변경 이유는 [../HISTORY.md](../HISTORY.md) 참고.
> 상세 사전조사는 [research/](research/README.md)로 분리했다.

## 한 줄 정의

> 추가 인프라(비콘·Wi-Fi 측위맵·VPS 서버) 없이, 스마트폰 IMU 센서 + 건물 평면도만으로
> 동작하는 Map-Aided PDR 실내 내비게이션. 걸어 들어오면 자동으로 실내 지도로 전환된다.

## 사전조사 문서 (research/)

| 번호 | 문서 | 내용 |
|---|---|---|
| 00 | [문제 정의와 범위](research/00-problem-and-scope.md) | 무엇을·누구를 위해·어디까지 |
| 01 | [PDR](research/01-pdr.md) | 걸음 감지·보폭 추정 |
| 02 | [센서 융합·방향](research/02-sensor-fusion-heading.md) | IMU/AHRS, 드리프트 보정 |
| 03 | [지도 매칭](research/03-map-matching.md) | Particle Filter (핵심 차별점) |
| 04 | [실내-실외 전환](research/04-indoor-outdoor-transition.md) | GPS 자동 핸드오버 |
| 05 | [기기 센서 호환성](research/05-device-sensor-compatibility.md) | 아이폰·갤럭시 매트릭스 |
| 06 | [기술 스택·데이터 포맷](research/06-tech-stack.md) | Flutter·FastAPI·GeoJSON |
| 07 | [경쟁/유사 솔루션](research/07-related-work.md) | Mapsted·Google·Naver |
| 08 | [평가·데모 설계](research/08-evaluation.md) | CDF/CE75, A/B 비교 |

## 조사 진행 현황

| 구분 | 확인할 내용 | 상태 |
|---|---|---|
| 사용자 문제 | 실내에서 GPS 끊김 → 길찾기 불가 | Done ([00](research/00-problem-and-scope.md)) |
| 데이터 소스 | 평면도 GeoJSON(벽/복도/문/POI) | Done ([06](research/06-tech-stack.md)) |
| 측위 알고리즘 | PDR + Particle Filter 지도 매칭 | Done ([01](research/01-pdr.md)·[03](research/03-map-matching.md)) |
| 방향 추정 | AHRS 센서 융합(Complementary/Madgwick) | Done ([02](research/02-sensor-fusion-heading.md)) |
| 자동 전환 | GPS 입구 매칭 + accuracy 급락 | Done ([04](research/04-indoor-outdoor-transition.md)) |
| 기기 호환성 | 자이로 필수, 기압계 권장 | Done ([05](research/05-device-sensor-compatibility.md)) |
| 경쟁 솔루션 | Mapsted/Google VPS/Naver 비교 | Done ([07](research/07-related-work.md)) |
| 평가 방식 | CDF/CE75, Baseline vs Ours A/B | Done ([08](research/08-evaluation.md)) |
| UI 레퍼런스 | 평면도 위 실시간 마커·경로 | Todo |

## 다음 할 일

- [ ] UI/화면 레퍼런스 수집(평면도 렌더링, 실시간 마커, 경로 표시)
- [ ] 데모용 타겟 건물·평면도 확보(직접 측량 또는 도면 입수)
- [ ] [navigation-overview.md](navigation-overview.md)의 일반 스택 가정을 실제 주제(Flutter+PDR)로 갱신
- [ ] [../VERSION.md](../VERSION.md)의 컴포넌트 표를 실제 스택(Flutter/FastAPI/Dart 알고리즘)으로 갱신
