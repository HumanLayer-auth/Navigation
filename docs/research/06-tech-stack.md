# 06. 기술 스택과 데이터 포맷

플랫폼: **Flutter(크로스플랫폼) + FastAPI(백엔드)** 풀스택. 핵심 알고리즘은 Dart로 직접 구현.

## 프론트엔드 (Flutter)

| 역할 | 패키지/기술 | 메모 |
|---|---|---|
| 앱 프레임워크 | Flutter 3.x (Dart) | |
| 센서 수집 | `sensors_plus` | 가속도계·자이로·지자기 스트림 |
| 기압계 | `sensors_plus`(플랫폼별) 또는 전용 플러그인 | 미탑재 기기 폴백 필요 |
| GPS | `geolocator` | 야외 위치 + accuracy 스트림, 실내 전환 트리거 |
| 나침반 보조 | `flutter_compass` | 플랫폼 fused heading 비교용(선택) |
| 지도 렌더링 | `flutter_map` + 평면도 오버레이 | OSM 어댑터, API 키 불필요. 평면도는 커스텀 레이어 |
| PDR/필터 | **Dart 직접 구현** | 걸음 감지·heading·Particle Filter |
| 상태 관리 | `Riverpod` (권장) 또는 `Bloc` | 센서 스트림 다수 → 상태 관리 중요 |

> **중요**: `geolocator`·`sensors_plus` 같은 표준 패키지는 **PDR/dead reckoning 기능을 제공하지 않는다.**
> 걸음 감지·방향 융합·지도 매칭은 전부 직접 구현해야 한다. 이게 곧 프로젝트의 기술적 본체다.

### 백그라운드 위치 주의

- 장시간 센서·GPS 구독은 배터리 소모가 크다. 백그라운드 위치 플러그인은 배터리 영향이 크므로
  **데모는 포그라운드 동작 위주**로 설계하고, 배터리 이슈는 발표에서 "향후 최적화"로 언급.

## 핵심 알고리즘 (Dart)

| 모듈 | 내용 | 참고 문서 |
|---|---|---|
| `step_detector` | 가속도 magnitude → LPF → peak detection | [01](01-pdr.md) |
| `stride_estimator` | Weinberg 보폭 모델 + 키 입력 | [01](01-pdr.md) |
| `heading_filter` | Complementary/Madgwick (자이로+지자기 융합) | [02](02-sensor-fusion-heading.md) |
| `pdr_engine` | 위 셋 통합 → 위치 델타 | [01](01-pdr.md) |
| `particle_filter` | 평면도 제약 매칭 | [03](03-map-matching.md) |
| `io_transition` | GPS→실내 전환 감지·초기화 | [04](04-indoor-outdoor-transition.md) |
| `route_planner` | 평면도 그래프 위 최단 경로(A*/Dijkstra) | [03](03-map-matching.md) 위상 매칭 |

## 백엔드 (FastAPI)

| 역할 | 기술 | 메모 |
|---|---|---|
| 서버 프레임워크 | Python 3.12 + **FastAPI** | REST 방식으로 엔드포인트 설계 |
| 평면도/건물 저장 | 정적 GeoJSON 파일 (1차) → PostgreSQL/Firestore(확장) | 데모는 파일만으로 충분 |
| 지도 서빙 | GeoJSON / (선택) PNG 타일 | |
| 배포 | Railway / Firebase Hosting 등 | 시연용 경량 배포 |

> FastAPI는 "도구(프레임워크)", REST는 "API 설계 방식"이라 레이어가 다르다.
> 이 규모에선 **FastAPI + REST** 조합 그대로면 충분(GraphQL 불필요).

### 예시 엔드포인트

```
GET /buildings                        # 건물 목록
GET /buildings/{id}                   # 건물 메타 + 입구 좌표
GET /buildings/{id}/floors/{floor}    # 해당 층 평면도 GeoJSON
```

## 평면도 데이터 구조

평면도는 **벽(통과 불가) + 보행가능 영역 + 문 + 관심지점(POI) + 경로 그래프**를 담아야 한다.
표준 GeoJSON Feature로 표현하고, `properties.type`으로 의미를 구분한다.

```
building/
├─ meta: { id, name, entrances: [ {lat, lng, floor, heading_hint} ] }
└─ floors/
   ├─ floor_1.geojson
   │   features:
   │     - type: "wall"      geometry: LineString   # Particle Filter 벽 제약
   │     - type: "corridor"  geometry: Polygon       # 보행가능 영역
   │     - type: "door"      geometry: Point         # 문 통과 관측
   │     - type: "poi"       geometry: Point  name:  # 목적지 후보
   │     - type: "node"/"edge"                        # 경로 그래프(최단경로용)
   └─ floor_2.geojson
```

좌표계 메모: 실내는 보통 **건물 로컬 좌표(미터)** 로 다루는 게 PDR 적분과 잘 맞는다.
GPS(위경도)와의 정합은 입구 좌표를 기준점(anchor)으로 변환한다.

## 전체 데이터 흐름

```
[휴대폰 센서] ── sensors_plus ──┐
[GPS] ── geolocator ───────────┤
                                ▼
                  io_transition (실내 진입 감지·초기화)
                                ▼
              pdr_engine (걸음·보폭·heading)
                                ▼
        particle_filter (평면도 제약 매칭)  ◄── 평면도 GeoJSON (FastAPI)
                                ▼
                  현재 위치 추정 (x, y, floor)
                                ▼
          flutter_map 평면도 위 실시간 마커 + 경로
```

## 구현 우선순위 (경진대회)

1. **PDR 동작** — 없으면 프로젝트 자체가 성립 안 함.
2. **평면도 렌더링** — 시각적으로 심사위원 눈에 바로 보임.
3. **Particle Filter** — 차별점, 완성도 급상승.
4. **자동 전환** — 시연 임팩트.
5. **백엔드** — 데모용이면 정적 GeoJSON 서빙으로 최소화하고 알고리즘에 집중.

## 참고 자료

- [sensors_plus | Flutter package](https://pub.dev/packages/sensors_plus)
- [geolocator | Flutter package](https://pub.dev/packages/geolocator)
- [Top Flutter Map and Geolocation Utility packages | Flutter Gems](https://fluttergems.dev/geolocation-utilities/)
- [Flutter Sensors Tutorial: Accelerometer, Gyroscope & GPS (Mantra Ideas)](https://mantraideas.com/build-sensor-apps-flutter-examples/)
