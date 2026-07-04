# 더현대서울 Indoor Navigation Map 후처리

기존 추출 산출물인 `output/thehyundai_building.geojson`,
`output/thehyundai_building_summary.json`, `output/floor_assets/`를 입력으로 사용해
PDR + Particle Filter에서 사용할 수 있는 topology 기반 indoor map을 생성한다.

## 실행

```bash
source .venv/bin/activate
pip install -r requirements.txt
python scripts/build_navigation_map.py
python scripts/generate_preview.py
```

`requirements.txt`에는 EasyOCR가 포함되어 있다. OCR 없이 빠르게 topology와 debug 이미지만 생성하려면
다음처럼 실행한다.

```bash
python scripts/build_navigation_map.py --skip-ocr
python scripts/generate_preview.py
```

## 입력

- `output/floor_assets/json/map-*.json`
- `output/floor_assets/map_element_screenshot.png`
- `output/thehyundai_building.geojson`
- `output/thehyundai_building_summary.json`

## 출력

- `output/navigation_map.json`
- `output/navigation_map_parts/building.json`
- `output/navigation_map_parts/nodes.json`
- `output/navigation_map_parts/edges.json`
- `output/navigation_map_parts/stores.json`
- `output/navigation_map_parts/pois.json`
- `output/navigation_map_parts/ocr_results.json`
- `output/navigation_map_parts/image_analysis.json`
- `output/preview.html`
- `output/debug/corridors.png`
- `output/debug/navigation_graph.png`
- `output/debug/ocr_result.png`
- `output/debug/stores.png`
- `output/debug/final_navigation_map.png`

## 구조

`navigation_map.json`은 이제 큰 데이터를 직접 담지 않고 split manifest 역할만 한다. 실제 데이터는
`output/navigation_map_parts/`에 분리 저장된다.

- `navigation_map_parts/nodes.json`: A*/Dijkstra에서 바로 사용할 routing node
- `navigation_map_parts/edges.json`: 양방향 이동 가능 edge와 meter length
- `navigation_map_parts/stores.json`: 매장명, centroid, entrance, polygon/bbox, confidence
- `navigation_map_parts/pois.json`: 엘리베이터, 에스컬레이터, 출구, 화장실 등 주요 POI
- `navigation_map_parts/ocr_results.json`: EasyOCR 결과와 confidence
- `navigation_map_parts/manual_review_candidates.json`: 낮은 confidence 또는 검토가 필요한 객체

앱에서 매장 검색만 필요하면 `stores.json`만 읽고, 경로 탐색은 `nodes.json`과 `edges.json`만 읽으면 된다.

좌표계는 `local_meters_top_left`이다. Dabeeo의 전체 `3000x3000` 캔버스가 아니라 실제 1F에서
매장/POI/node가 차지하는 `floor_bounds_source`를 계산한 뒤, 이 bounds를 VWorld 건물 외곽 bbox 크기에
선형 매핑한다.

화면 미리보기와 debug overlay는 bounds 추정만 쓰지 않는다. Dabeeo object polygon mask와 실제
층 안내도 스크린샷의 회색 매장 mask를 OpenCV `findTransformECC`로 정합해
`image_analysis.source_to_image_affine` 행렬을 만들고, 이 affine으로 모든 node/store/POI를 이미지 위에
표시한다. 정합 품질은 `output/debug/calibration.png`와 `navigation_map.json`의
`initial_dice`, `final_dice`에서 확인한다.

CAD 수준의 치수 정확도보다 graph topology 보존을 우선한다.
