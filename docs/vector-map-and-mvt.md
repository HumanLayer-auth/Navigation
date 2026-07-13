# 벡터 지도 생성과 MVT 데이터

## 1. 문서 목적

이 문서는 SVG·CAD·BIM 등으로 만든 지도 원본을 앱에서 사용할 수 있는 벡터 지도 데이터로 변환하고, 필요할 때 MVT(Mapbox Vector Tile)로 배포하는 전체 구조를 설명한다.

현재 프로젝트의 실내 지도에는 다음 목표를 적용한다.

- 서울창업허브의 층 평면도를 벡터로 렌더링한다.
- 팀메이킹룸 3 입구 같은 공간·출입 노드를 경로 그래프와 연결한다.
- PDR 현재 위치와 이동 궤적은 고정 지도 데이터와 분리된 실시간 레이어로 그린다.
- 단일 건물 단계에서는 불필요한 타일 서버를 도입하지 않고, 여러 건물·층으로 확장할 때 MVT를 적용한다.

## 2. 지도 데이터의 세 가지 층

지도는 하나의 이미지가 아니라 고정 데이터, 경로 데이터, 실시간 상태를 분리해서 관리한다.

```text
고정 지도 데이터
  ├─ 벽, 방, 복도, 계단, 엘리베이터
  ├─ POI와 라벨
  └─ 지도 스타일

경로 데이터
  ├─ 노드(node)
  ├─ 간선(edge)
  └─ 층간 연결

실시간 오버레이
  ├─ GPS 또는 PDR 현재 위치
  ├─ 이동 궤적
  ├─ 계산된 경로
  └─ 센서 품질·안내 상태
```

PDR 위치와 궤적은 MVT나 SVG에 미리 굽지 않는다. 앱에서 센서 이벤트가 들어올 때마다 지도 좌표계로 변환해 별도 레이어로 갱신한다.

## 3. SVG·래스터·벡터 타일 비교

### SVG

SVG는 선과 도형을 표현하는 편집·교환 형식이다. 디자인 원본과 검수용으로 적합하지만, SVG 전체를 런타임에 WebView로 표시하면 앱 안에 웹 렌더링 계층이 생긴다.

SVG의 문제점은 다음과 같다.

- 큰 문서의 요소 탐색과 이벤트 처리가 무거워질 수 있다.
- 지도 좌표계·타일 분할·일반화가 정의되어 있지 않다.
- PDR과 경로 그래프가 SVG DOM 구조에 강하게 결합될 수 있다.
- 모바일 지도 SDK의 카메라·피킹·오프라인 캐시 모델과 직접 맞지 않는다.

따라서 SVG는 원본으로 보관하고, 앱용 데이터로 변환하는 편이 좋다.

### 래스터 타일

PNG 또는 WebP 이미지 타일이다. 큰 지도를 여러 이미지 조각으로 나누어 필요한 타일만 받는다.

장점:

- 구현과 배포가 단순하다.
- 위성·항공 사진처럼 이미지 자체가 필요한 경우에 적합하다.

단점:

- 확대하면 흐려진다.
- 방·매장·노드의 선택과 속성 조회가 어렵다.
- 색상·라벨·선 굵기를 런타임에 바꾸기 어렵다.

### 벡터 타일

벡터 타일은 이미지가 아니라 폴리곤·라인·점·속성을 담은 작은 데이터 조각이다. 앱의 지도 렌더러가 데이터를 받아 GPU로 그린다.

```text
벡터 타일 + 스타일
        ↓
지도 렌더러
        ↓
폴리곤·선·라벨·아이콘
```

벡터 타일은 보통 줌·열·행 좌표로 나뉜다.

```text
/{z}/{x}/{y}
```

## 4. MVT란 무엇인가

MVT(Mapbox Vector Tile)는 벡터 지도를 타일 단위로 저장하고 전송하는 대표 형식이다. 이미지가 아니라 Protocol Buffers 기반의 바이너리 데이터이며, 타일 안에 여러 레이어와 피처가 들어간다.

예시 개념:

```text
tile z/x/y
  ├─ layer: walls
  │    └─ polygon geometry
  ├─ layer: rooms
  │    └─ polygon + room_id + name
  ├─ layer: corridors
  │    └─ line geometry
  └─ layer: poi
       └─ point + poi_type + label
```

MVT에는 보통 다음이 들어간다.

- geometry: point, line, polygon
- properties: 이름, 종류, ID, 층, 카테고리
- layer: 벽·공간·복도·POI 등 데이터 그룹
- feature ID: 선택·이벤트·업데이트에 사용할 식별자

MVT 자체에는 보통 화면 색상이나 폰트가 들어 있지 않다. 스타일 JSON 또는 앱 코드가 피처 속성에 따라 렌더링 방법을 결정한다.

## 5. MVT 생성 파이프라인

```text
SVG / CAD / BIM / GeoJSON
          ↓
도형 추출·정리
          ↓
좌표계 정의 및 단위 변환
          ↓
공간·POI·그래프 분리
          ↓
GeoJSON 또는 공간 DB 적재
          ↓
MVT 생성
          ↓
타일 서버·MBTiles·오프라인 패키지
          ↓
앱 지도 렌더러
```

### 5.1 원본 정리

SVG에서 다음 요소를 명확히 분리한다.

- 벽과 외곽선
- 공간·방·매장 polygon
- 복도·통행 가능 영역
- POI와 라벨
- 출입구·계단·엘리베이터
- 그래프 노드와 edge

원본 도형의 ID는 변환 후에도 유지한다. 예를 들어 팀메이킹룸 3 입구는 `N17`처럼 안정적인 ID를 갖도록 한다.

### 5.2 좌표계 정의

실내 지도는 지리 좌표보다 로컬 미터 좌표가 적합하다.

```text
floor_local_m
  x: 동쪽 방향(m)
  y: 북쪽 방향(m)
```

SVG가 픽셀 단위라면 변환 비율과 원점을 명시한다.

```text
svg_x = origin_x + floor_x * pixels_per_meter
svg_y = origin_y - floor_y * pixels_per_meter
```

SVG의 화면 y축은 아래 방향이고, 일반적인 지도·PDR 좌표의 north 축은 위 방향일 수 있으므로 부호 반전을 반드시 문서화한다.

### 5.3 GeoJSON 중간 형식

MVT를 만들기 전에 GeoJSON을 중간 산출물로 두면 검수와 테스트가 쉬워진다.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "room-team-making-3",
      "properties": {
        "layer": "rooms",
        "name": "팀메이킹룸 3",
        "floor": "1F"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[44.0, 29.0], [45.0, 29.0], [45.0, 31.0], [44.0, 31.0], [44.0, 29.0]]]
      }
    }
  ]
}
```

단, GeoJSON의 좌표 순서와 프로젝트 내부의 `x/y` 의미를 혼동하지 않는다. 변환 단계에서 한 번만 명확히 바꾼다.

### 5.4 타일 분할

타일 생성기는 geometry를 타일 경계에 맞춰 잘라내고, 필요하면 줌 단계에 따라 단순화한다.

- 낮은 줌: 작은 선·라벨을 제거하거나 단순화
- 높은 줌: 상세 벽·공간·POI 유지
- 타일 경계: geometry clipping과 buffer 적용
- 피처 ID: 타일이 바뀌어도 선택 이벤트가 이어지도록 안정적으로 유지

## 6. 대표적인 생성·배포 방식

### 파일 기반

작은 프로젝트에서는 GeoJSON 또는 자체 `floor.json`을 앱 에셋으로 포함한다.

```text
floor.json → Flutter CustomPainter 또는 Canvas
```

서울창업허브처럼 건물과 층이 적고 오프라인 테스트가 중요하면 이 방식이 가장 단순하다.

### MBTiles 기반

MVT 타일을 하나의 SQLite 컨테이너인 `.mbtiles` 파일로 묶어 배포한다. 앱이 파일에서 필요한 `z/x/y` 타일을 읽는다.

장점:

- 네트워크 없이 동작한다.
- 건물 단위 오프라인 패키지를 만들기 쉽다.

### 타일 서버 기반

서버가 `/{z}/{x}/{y}.mvt` 요청에 맞춰 타일을 반환한다. 공간 DB를 쓰면 데이터 변경 후 타일을 동적으로 만들 수 있다.

```text
PostGIS / 파일 저장소
          ↓
MVT 타일 서버
          ↓
모바일 지도 SDK
```

대표적으로 다음 조합을 고려할 수 있다.

- GeoJSON → tippecanoe → MBTiles
- PostGIS → `ST_AsMVT` → API
- MBTiles 또는 PostGIS → Martin/Tegola 계열 타일 서버
- MapLibre Native → 모바일 벡터 렌더링

도구 선택은 프로젝트의 운영 환경과 라이선스를 확인한 뒤 결정한다.

## 7. 실내 지도에서 MVT를 적용하는 방법

실내 지도는 전 세계 지도를 나누는 일반적인 Web Mercator 타일과 달리, 건물 로컬 좌표계를 사용할 수 있다.

두 가지 방식이 있다.

### 방식 A: 타일 없이 층 단위 벡터 파일

```text
building_id/thehyundai-seoul/1F.json
building_id/seoul-startup-hub/1F.json
```

단일 건물이나 초기 프로토타입에 적합하다.

### 방식 B: 층별 로컬 MVT

각 층을 독립적인 로컬 타일셋으로 만들고, 지도 카메라가 요청하는 영역만 읽는다.

```text
building_id/floor_id/{z}/{x}/{y}.mvt
```

타일 메타데이터에 반드시 넣어야 할 정보:

- 건물 ID와 층 ID
- 좌표 원점
- x/y 축 방향
- 단위와 pixels-per-meter 또는 meters-per-tile
- 지도 bounds
- 기준 회전각

실내 MVT는 일반 지리 지도와 섞어 쓰지 않고, 실외 좌표와 실내 좌표 사이의 전환 정보를 별도로 관리하는 편이 안전하다.

## 8. PDR 오버레이와 좌표 변환

PDR은 센서 로컬 좌표를 지도 좌표로 변환해야 한다.

```text
floor_point = R(rotation) × pdr_point + anchor
```

여기서:

- `pdr_point`: PDR이 계산한 동쪽·북쪽 이동량
- `rotation`: 기기 heading과 층 도면 축의 차이
- `anchor`: 세션 시작점의 층 좌표
- `floor_point`: 지도에 그릴 최종 위치

팀메이킹룸 3 입구에서 시작하는 경우:

```text
anchor_node = N17
anchor_point = N17의 floor_local_m 좌표
```

앱은 MVT를 바꾸지 않고 다음만 갱신한다.

- 현재 위치 marker
- 지나온 궤적 polyline
- 목표까지의 경로 polyline
- 센서 품질과 보정 상태

## 9. 렌더러 선택

### Flutter Canvas/CustomPainter

현재 프로젝트에 가장 적합한 1단계 선택이다.

- iOS·Android에서 동일한 지도 코드를 공유한다.
- SVG를 path로 변환하거나 JSON geometry를 직접 그릴 수 있다.
- PDR 오버레이를 같은 좌표계에 쉽게 그릴 수 있다.
- 단일 건물에서는 타일 서버가 필요 없다.

### MapLibre Native

다음 요구가 생기면 고려한다.

- 여러 건물과 층
- 큰 데이터셋
- 스타일 기반 벡터 레이어
- 오프라인 타일 패키지
- 실외 지도와 연속된 카메라·줌

MapLibre는 iOS와 Android 모두에서 벡터 타일과 스타일 기반 렌더링을 제공한다.

### 플랫폼 네이티브 렌더러

- iOS: Core Graphics, SwiftUI Canvas, Metal, 또는 MapKit 커스텀 오버레이
- Android: Canvas, Jetpack Compose Canvas, 또는 MapLibre Native

플랫폼별 구현은 최종 성능·카메라·제스처를 극한까지 제어할 때 선택한다. 초기에는 Flutter 공통 렌더러가 유지보수 비용이 낮다.

## 10. 현재 프로젝트 권장 단계

### 1단계: 단일 층·PDR 검증

```text
demo_floor_map_v5.svg
        ↓
서울창업허브 floor JSON
        ↓
Flutter Canvas 벡터 지도
        ↓
N17 팀메이킹룸 3 입구 앵커
        ↓
PDR marker·궤적 오버레이
```

이 단계에서는 실내 지도 화면이 FastAPI에 의존하지 않도록 로컬 에셋을 사용한다.

### 2단계: API 기반 층 데이터

FastAPI가 건물·층·POI·그래프를 반환한다.

```text
GET /buildings/{building_id}
GET /buildings/{building_id}/floors/{floor_id}
GET /buildings/{building_id}/floors/{floor_id}/graph
```

앱은 고정 geometry와 그래프를 API에서 받아도 렌더링 방식은 동일하게 유지한다.

### 3단계: MVT와 스타일 서버

```text
원본 편집 데이터
        ↓ CI 변환
MVT + style.json + graph.json
        ↓ CDN/타일 서버/오프라인 패키지
모바일 벡터 렌더러
```

이때 PDR은 계속 앱 런타임 오버레이로 남긴다.

## 11. 검증 체크리스트

### 데이터

- 모든 feature에 안정적인 ID가 있는가?
- SVG 픽셀 좌표와 floor meter 좌표의 변환식이 문서화되었는가?
- SVG y축과 PDR north 축의 부호가 맞는가?
- 팀메이킹룸 3 입구가 `N17`로 연결되는가?
- 그래프 edge가 벽을 통과하지 않는가?

### 렌더링

- 확대·축소 시 도형이 선명한가?
- 방·복도·POI 레이어를 독립적으로 켜고 끌 수 있는가?
- 피처를 탭하면 원래 ID와 속성을 얻는가?
- PDR marker가 지도와 같은 카메라 변환을 적용받는가?

### 운영

- 온라인 불가 시 마지막 층 데이터를 사용할 수 있는가?
- 타일 또는 층 데이터 버전을 추적할 수 있는가?
- 스타일 변경과 geometry 변경을 분리 배포할 수 있는가?
- PDR 궤적을 서버 지도 데이터와 혼합하지 않는가?

## 12. 결론

MVT는 SVG 이미지 조각이 아니라, 지도 도형과 속성을 타일 단위로 저장·전송하는 바이너리 벡터 데이터다. 상용 지도에 가까운 구조는 다음과 같다.

```text
원본 SVG/CAD
  → 정규화된 공간·POI·그래프 데이터
  → 필요할 때 MVT 타일
  → 네이티브/Flutter 벡터 렌더러
  → PDR 실시간 오버레이
```

서울창업허브 단일 층의 현재 목표에는 `floor.json + Flutter Canvas + PDR 오버레이`가 적합하다. 향후 여러 건물·층과 오프라인 지도 규모로 확장할 때 `MVT + 스타일 + MapLibre Native`로 발전시키면 된다.
