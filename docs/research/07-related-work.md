# 07. 경쟁/유사 솔루션 (Related Work)

우리 위치를 명확히 하기 위한 경쟁·유사 솔루션 정리. **차별점 = "인프라 0 + 개인 단독 동작"**.

## 상용 솔루션

### Mapsted

- 비콘·Wi-Fi 등 외부 하드웨어 없이 스마트폰 센서만으로 실내 내비를 제공하는 **B2B 플랫폼**.
- 건물주/기업이 도입해 그 시설 앱에 탑재되는 방식 → **개인이 앱스토어에서 받는 게 아님.**
- 한국어 페이지(en-kr)는 존재하나 국내 실제 도입 사례는 공개적으로 확인되지 않음.
- 위치 기반 마케팅(타겟 광고/프로모션)에 강점, 반면 지도 기능·연동은 제한적이라는 평가.
- **우리와의 관계**: 기술 철학(인프라리스)은 유사하나, Mapsted는 폐쇄형 B2B. 우리는
  "평면도 한 장 + 개인 폰" 오픈 데모로 차별화.

### Google — ARCore Geospatial API / VPS

- Street View 수백억 장 기반 **Visual Positioning Service(VPS)**. 위경도+고도로 콘텐츠 앵커링,
  87개국 이상 지원, GPS보다 높은 정확도.
- **약점(우리 관점)**: 사전 구축된 방대한 이미지 맵 서버에 의존. 임의의 건물 내부, 특히
  Street View 없는 실내는 커버 못 함. 개인이 새 건물을 즉석에서 못 만듦.

### Apple — Indoor Maps / ARKit

- ARKit는 LiDAR·depth로 정밀 측위 가능. Apple Indoor Maps는 Mapsted 등과 연계.
- **약점**: 시설측이 Apple에 평면도를 등록(IMDF)해야 하고, 정밀 모드는 LiDAR 탑재 기기 의존.

### Naver 지도 (국내)

- COEX 등 복합시설에 실내 지도·AR 워킹 가이드(실제 거리 위 방향 화살표 오버레이) 배포.
- 공항·쇼핑몰·지하상가 실내 지도 제공.
- **약점(우리 관점)**: 네이버가 직접 매핑/구축한 대형 시설에 한정. 일반 건물은 미지원.

### Mappedin 등 실내 매핑/웨이파인딩 SaaS

- 실내 지도 제작·웨이파인딩 소프트웨어. 역시 B2B·사전 매핑 모델.

## 측위 기술 갈래 비교

| 기술 | 인프라 요구 | 정확도 | 개인 단독 사용 |
|---|---|---|---|
| **PDR + Map Matching (우리)** | 평면도 1장 | 복도 1~3m | **가능** |
| BLE 비콘 | 비콘 설치 | 1~3m | 불가(설치 필요) |
| Wi-Fi Fingerprinting | 측위맵 구축 | 2~5m | 불가(사전 측정) |
| VPS (카메라) | 3D/이미지 맵 서버 | <1m | 불가(맵 의존) |
| 시각 마커(QR/AR마커) | 마커 부착 | 마커 근처 정밀 | 부분(부착 필요) |

## 우리의 포지셔닝

```
모든 상용 솔루션의 공통 전제 = "누군가 사전 인프라를 구축해야 한다"
   (비콘 설치 / Wi-Fi 측위맵 / VPS 3D맵 / 시설측 IMDF 등록)

우리의 주장 = "평면도 한 장만 있으면, 그 외 인프라 0으로 동작한다"
```

- **강점**: 진입 장벽 최소(평면도만 있으면 어떤 건물도 빠르게 적용), 하드웨어/서버 비용 0,
  프라이버시(센서 로컬 처리).
- **정직한 한계**: 절대 정밀도는 VPS·비콘보다 낮고, 넓은 홀에서 매칭 효과 감소,
  초기 위치 확정 필요(→ 자동 전환으로 해결, [04](04-indoor-outdoor-transition.md)).
- 발표에서는 **"정밀도 1등"이 아니라 "비용·접근성·확장성에서 압도적"** 이라는 프레임이 유리.

## 차별점 정리 (발표용 한 줄)

> "상용 실내 내비는 전부 사전 인프라가 필요하다. 우리는 평면도 한 장과 폰 센서만으로,
> 야외에서 걸어 들어오면 자동으로 실내 길찾기가 시작되는 경험을 만든다."

## 참고 자료

- [Google Maps Indoors: Is There a Better Alternative? (Mapsted blog)](https://mapsted.com/blog/google-indoor-maps-and-alternatives)
- [Mapsted Indoor Navigation — Turn-by-Turn Without Hardware](https://mapsted.com/indoor-navigation)
- [Build location-based AR with the ARCore Geospatial API (Google for Developers)](https://developers.google.com/ar/develop/geospatial)
- [Ultimate guide to indoor mapping & wayfinding software (Mappedin)](https://www.mappedin.com/resources/blog/indoor-mapping-wayfinding-software-guide/)
- [AR Indoor Navigation Application Development Guide (MobiDev)](https://mobidev.biz/blog/augmented-reality-indoor-navigation-app-development)
