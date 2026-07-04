# 더현대서울 Indoor Navigation Dataset

이 폴더는 더현대서울 실내 내비게이션 데모를 위해 생성한 로컬 데이터셋이다.
VWorld 건물 외곽, 현대백화점 모바일 층 안내도 공개 리소스, 후처리된 topology 기반
navigation graph를 함께 보관한다.

CAD 도면처럼 정밀한 실측 데이터가 아니라, PDR + Particle Filter 데모에서 경로 탐색과
위치 보정을 실험할 수 있는 수준의 topology map이다.

## 핵심 파일

- `navigation_map.json`: 전체 데이터를 직접 담지 않는 split manifest. 앱은 이 파일에서 `files` 경로를 읽어 필요한 JSON만 로드한다.
- `navigation_map_parts/nodes.json`: 길찾기 그래프의 node 목록. 각 node에는 `id`, `type`, `position.local_meters`, `position.source`, `confidence`가 들어간다.
- `navigation_map_parts/edges.json`: node 간 이동 가능한 edge 목록. A* 또는 Dijkstra에서 바로 사용할 수 있도록 `from`, `to`, `length_m`, `bidirectional`, `confidence`를 포함한다.
- `navigation_map_parts/stores.json`: 매장 데이터. `id`, `name`, `centroid`, `entrance`, `polygon` 또는 `bbox`, `confidence`, OCR 매칭 정보가 들어간다.
- `navigation_map_parts/pois.json`: 엘리베이터, 에스컬레이터, 계단, 출입구, 화장실 등 POI 후보.
- `navigation_map_parts/ocr_results.json`: EasyOCR로 읽은 텍스트 원본과 bounding box, confidence.
- `navigation_map_parts/manual_review_candidates.json`: confidence가 낮거나 자동 추출 품질 검수가 필요한 객체.
- `preview.html`: 브라우저에서 지도, 그래프, 매장, OCR, POI overlay를 확인하는 미리보기.

## 좌표계

- `position.source`: Dabeeo 지도 JSON 원본 좌표계.
- `position.local_meters`: 건물 외곽 크기에 맞춰 변환한 실내 로컬 meter 좌표계. 길찾기와 PDR 데모에서는 이 값을 우선 사용한다.
- `position.wgs84`: 가능한 경우 WGS84 위경도 추정값. 실내 데모의 주 좌표계로 쓰기보다는 외부 지도 연동용 보조값으로 본다.
- `navigation_map_parts/coordinate_system.json`: 좌표 변환 기준, scale, source bounds, 건물 bbox 정보를 담는다.
- `navigation_map_parts/image_analysis.json`: 실제 스크린샷 위에 overlay를 맞추기 위한 OpenCV affine 정합 결과를 담는다.

## 앱에서 읽는 방법

매장 검색만 필요하면 다음 파일만 읽으면 된다.

```text
navigation_map_parts/stores.json
```

경로 탐색은 다음 두 파일을 사용한다.

```text
navigation_map_parts/nodes.json
navigation_map_parts/edges.json
```

POI 안내까지 포함하려면 다음 파일을 추가로 읽는다.

```text
navigation_map_parts/pois.json
```

시각화나 디버깅 UI는 `navigation_map.json` manifest를 먼저 읽고, `files`에 적힌 상대 경로를 따라
필요한 part 파일을 lazy load하는 방식이 가장 단순하다.

## 원천/중간 산출물

- `thehyundai_building.geojson`: VWorld GIS건물통합정보 SHP에서 추출한 더현대서울 건물 외곽.
- `thehyundai_building_summary.json`: centroid, 면적, 둘레, bbox, CRS 등 건물 외곽 요약.
- `thehyundai_dataset_summary.json`: 원천 추출 단계의 통합 요약.
- `floor_assets/manifest.json`: 현대백화점 모바일 층 안내도 페이지에서 브라우저가 공개적으로 받은 리소스 목록.
- `floor_assets/json/`: 저장된 JSON/GeoJSON 리소스. `map-*.json`이 층 도면의 핵심 원천이다.
- `floor_assets/images/`: 저장된 이미지/SVG 리소스.
- `floor_assets/page_screenshot.png`: 모바일 페이지 전체 스크린샷.
- `floor_assets/highres_screenshot.png`: 고해상도 캡처.
- `floor_assets/map_element_screenshot.png`: 가능할 때 도면 컨테이너만 캡처한 이미지.

## Debug 이미지

- `debug/corridors.png`: OpenCV 기반 복도 후보 추출 결과.
- `debug/walls.png`: 벽 후보 추출 결과.
- `debug/stores.png`: 매장 영역 후보 overlay.
- `debug/ocr_result.png`: OCR bounding box와 텍스트 후보.
- `debug/navigation_graph.png`: node/edge graph overlay.
- `debug/final_navigation_map.png`: 매장, POI, graph를 합친 최종 overlay.
- `debug/calibration.png`: Dabeeo 원본 좌표와 스크린샷 사이의 정합 품질 확인 이미지.
- `debug/preview_screenshot.png`: `preview.html` 렌더링 검증 캡처.

## 재생성

루트 디렉토리에서 다음 순서로 실행한다.

```bash
source .venv/bin/activate
python scripts/extract_thehyundai_building.py
python scripts/extract_ehyundai_floor_assets.py
python scripts/build_thehyundai_dataset.py
python scripts/build_navigation_map.py
python scripts/generate_preview.py
```

OCR 없이 빠르게 graph만 다시 만들려면 다음처럼 실행한다.

```bash
python scripts/build_navigation_map.py --skip-ocr
python scripts/generate_preview.py
```

## 주의

- 이 데이터셋은 데모용 자동 추출 결과다. 실제 서비스나 안전-critical 길안내에는 수동 검수와 현장 검증이 필요하다.
- confidence가 낮은 객체는 `navigation_map_parts/manual_review_candidates.json`에서 먼저 확인한다.
- 현대백화점 공개 페이지에서 브라우저가 정상적으로 받은 리소스만 저장한다. 로그인 우회나 비공개 API 접근 결과는 포함하지 않는다.
