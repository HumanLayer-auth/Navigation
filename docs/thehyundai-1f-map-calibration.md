# 더현대 서울 1F 지도 좌표 보정

## 결론

현재 1F `local_m` 왜곡의 주원인은 Dabeo topology나 PDR 센서가 아니라, 과거
`scripts/build_navigation_map.py::make_transform`이 회전된 VWorld 건물의 축 정렬
bbox 폭·높이를 Dabeo source bounds에 각각 독립 적용한 데 있다.

이번 변경은 구조 정합, 물리 scale, WGS84 지오리퍼런스를 분리했다.

```text
Dabeo source --robust affine--> SVG px --uniform m/px--> physical local_m
                                          |
                                          +--verified rigid georef--> WGS84
```

`172.0m × 100.6m`는 매우 일관된 후보지만 같은 구조 꼭짓점이라는 증거가 아직
없다. 따라서 현재 production Studio JSON은 덮어쓰지 않았으며 생성기도 이를
강제로 거부한다.

## 원격 및 이력 확인

- 작업 전 `origin/dev`를 fetch했고 로컬 `dev`를 `774d07d`까지 fast-forward했다.
- 최신 원격에는 PDR graph-constrained matching과 snapped start anchor가 이미 포함돼 있다.
- Studio 변환은 `9340802`에서 도입됐고 `f729e81`, `f854beb` 이후에도 1F의
  `x=0.06697499198`, `y=0.09328893119` 비등방 scale은 유지됐다.
- 과거 `make_transform`은 EPSG:5186 bbox `123.91 × 121.09m`를 source bounds
  `1850.15 × 1298.04`에 축별로 맞췄다.

## 구조 대응 근거

버전 관리된 입력:

- Dabeo raw: `thehyundai_indoor_navigation_dataset/navigation_map_parts/stores.json`
- 원본 SVG: `client/assets/mock/hyundai_floor_map.svg`
- calibration: `backend/resources/calibration/thehyundai-seoul/1f.json`
- 생성 보고서: `backend/resources/calibration/thehyundai-seoul/1f-report.json`

이름은 공백·기호를 제거한 뒤 alias를 적용한다. 61개 Dabeo 매장과 59개 SVG
매장 중 58개가 대응됐다. deterministic RANSAC affine 결과:

- inlier: `56 / 58`
- RMSE: `1.468px`
- 중앙값: `0.480px`
- 최대 inlier 잔차: `9.394px`
- outlier: `셀린느 120.67px`, `보테가 베네타 26.52px`
- affine 선형부 singular value 비: `1.00183` (거의 동일 배율)

```text
svg_x = 1.2021085010 source_x + 0.0020080587 source_y - 796.9360157
svg_y = 0.0001891760 source_x + 1.2022069425 source_y - 1148.2317921
```

즉 Dabeo와 SVG 구조는 강하게 일치하며, 기존 종횡비 오류는 후단 meter 변환에서
생겼다는 근거가 충분하다.

## 절대 scale과 VWorld 검증

SVG footprint bounds는 `(14, 52) – (2030, 1232)`, 즉 `2016 × 1180px`, 비율
`1.708475`다.

Naver 후보를 이 두 선분에 대응시킬 경우:

- `172.0 / 2016 = 0.08531746m/px`
- `100.6 / 1180 = 0.08525424m/px`
- 두 값의 상대 spread: 약 `0.074%`

하지만 Naver 측정 선의 실제 양 끝점 캡처/URL/해시가 없으므로 calibration에는
`status: hypothesis`, `same_vertices_confirmed: false`로 기록했다.

VWorld 실제 polygon은 minimum rotated rectangle가 약 `126.02 × 68.01m`, 비율
`1.853`, 면적 `7062.30m²`다. SVG/Naver 후보와 같은 전체 구조인지 불명확하므로
형상·방향·위치 검증 자료로만 사용하고 bbox 및 절대 scale 입력으로 사용하지 않는다.

## 재생성 동작

분석 보고서 재생성:

```powershell
cd backend
python -m scripts.transform.calibrate_thehyundai_1f
```

production 데이터 적용:

```powershell
python -m scripts.transform.calibrate_thehyundai_1f --apply
```

적용 전 calibration에 다음이 모두 있어야 한다.

1. 두 Naver 측정의 동일 SVG 꼭짓점 확인 및 증거 URL/시각/해시
2. 합의된 단일 `meters_per_svg_px`
3. 실제 동일 꼭짓점 3개 이상의 `svg_px_to_wgs84` 행렬과 검증 상태

조건이 충족되면 한 실행에서 다음을 모두 다시 계산한다.

- node `position.local_m`과 WGS84
- edge의 모든 geometry 점과 polyline `length_m`
- store polygon/centroid/entrance와 WGS84
- SVG building footprint
- source→SVG→local_m→WGS84 행렬
- `map_calibration_version`

현재 Studio stores/footprint의 raw source는 과거 split 과정에서 유실됐다. 생성기는
기존 affine 역변환으로 이를 복원해 `*_source`에 보존하지만, provenance는
`recovered_from_legacy_local_m` 성격이다. 완전한 원본 보존을 위해서는 최신 Studio
통합 export도 후속으로 버전 관리해야 한다.

## PDR 변경 경계

변경하지 않은 범위:

- iOS `CMPedometer`/motion bridge
- Android step/heading bridge
- `indoor_pdr_core`의 걸음·보폭·heading 계산
- raw PDR step/distance/path

변경한 범위:

- bearing은 `0°=북, 90°=동`인 시계 방향이라는 계약에 맞춰 수동 회전 부호 수정
- node WGS84 affine에서 얻은 PDR 축을 직교 단위축으로 정규화하여 scale/shear 제거
- seed 시 edge polyline 전체와 재계산한 실제 길이 보존
- Studio→DB→API→Flutter→debug JSON으로 `map_calibration_version` 전달
- debug schema v3에서 raw/floor/matched 거리와 경로를 분리 기록

맵매처의 `1.25m`, `4m`, `3×` 전환값과 anchor `12m` 상한은 새 physical data와
10/30/50m 기기 로그가 없으므로 임의 조정하지 않았다.

## 검증 상태와 남은 게이트

자동 검증은 robust fit, SVG 비율, production gate, edge polyline 보존, API version,
PDR bearing/isometry/debug JSON을 대상으로 한다. 시각 검증과 10/30/50m 기기 검증은
physical scale/WGS84가 확정된 데이터가 생성된 뒤 수행해야 한다.

현재 판정: **구조 보정 파이프라인과 런타임 계약 구현 완료, production 1F 데이터
교체는 동일 꼭짓점 근거 부족으로 차단됨.**
