# dev PDR 통합 변경 요약

## 목적

이 문서는 `dev` 브랜치에 올리는 PDR(Pedestrian Dead Reckoning) 통합의 범위와
검증 방법을 기록한다. 실내 지도·길찾기·건물 데이터의 일반적인 기능 변경은
포함하지 않고, 휴대폰 센서 기반 보행 위치 추정과 그 지도 표시·디버깅에 필요한
변경만 포함한다.

## 추가된 구성

### 1. 순수 Dart PDR 엔진

`packages/indoor_pdr_core/`는 플랫폼에 의존하지 않는 PDR 계산 패키지다.

- 걸음 수와 거리의 확정 경로(초록선) 및 가속도 미리보기 경로(주황선)를 분리한다.
- heading smoothing, gyro hold, 자력계 품질, 보폭 추정, cadence, 품질 경고를 계산한다.
- PDR 세션 회귀 JSON fixture와 합성 단위 테스트를 포함한다.

### 2. Android·iOS 센서 브리지

각 플랫폼은 같은 Dart 이벤트 계약으로 센서 값을 전달한다.

- Android: `STEP_COUNTER`, rotation vector, gyro, accelerometer 및 자력계 정확도
- iOS: `CMPedometer`, device motion, Core Motion heading 정보
- 공통: start/stop, pedometer baseline reset/finalize, lifecycle pause/resume

필요한 네이티브 구현은 다음 파일에 있다.

- `client/android/app/src/main/kotlin/com/navigation/navigation_client/PdrMotionBridge.kt`
- `client/ios/Runner/PdrMotionBridge.swift`

### 3. 실내 지도 PDR 연결

실내 지도에서 `PDR 시작`을 누르면 사용자가 지도 위 현재 위치를 anchor로 고른다.

```text
센서 이벤트
  → indoor_pdr_core PdrSession
  → anchor 기준 floor_local_m 좌표
  → floor graph edge로 맵매칭
  → MapLibre PDR trail / blue-dot / heading pointer
```

- anchor 이후 확정 PDR 경로를 층 로컬 좌표로 바꾼다.
- `FloorMapMatcher`가 경로를 통행 그래프 edge에 투영해 벽·매장을 가로지르는
  센서 드리프트 표현을 줄인다.
- 맵매칭은 표시 안정화 장치이며, 센서 거리·heading 자체의 정확도를 보장하지는 않는다.
- 절대 heading을 신뢰할 수 없는 기기는 사용자가 지도 방향을 선택해 회전을 보정한다.

### 4. 디버그 JSON 공유

PDR 종료 뒤 지도 제어의 공유 아이콘 또는 스낵바의 `JSON 공유`로 시스템 공유창을 연다.

파일에는 분석에 필요한 최소 정보만 담는다.

- 시작·내보내기 시각, 앱/기기 정보, 건물·층·그래프 요약
- anchor와 회전 기준
- 확정 PDR 경로, 맵매칭 전후 경로
- 확정 걸음·거리·heading, 보폭/heading/자력계 품질 샘플(최대 1 Hz)

원시 IMU 전체 샘플, GPS 좌표, 개인정보는 포함하지 않는다. 현장 테스트 뒤에는
JSON 파일과 함께 실제 시작점·도착점·걸은 방식·알려진 거리를 전달해 분석한다.

## 의도적으로 포함하지 않은 변경

이번 PDR PR에는 다음을 넣지 않는다.

- 새 건물 목록 화면 및 `dio`/Riverpod 기반 데이터 계층
- 사용되지 않는 중복 전역 테마
- 일반 벡터 타일/MVT 설계 문서
- 개발 편의를 위한 iOS 전체 HTTP 허용(ATS)·로컬 네트워크 권한 완화
- 실내 지도와 무관한 API 동작 변경

## 의존성

PDR 기능을 위해 다음 Flutter 의존성을 추가한다.

- `indoor_pdr_core`: 순수 PDR 계산 패키지
- `share_plus`, `device_info_plus`, `package_info_plus`: 디버그 JSON 파일 공유와 최소 기기 식별
- `webview_flutter`: PDR SVG 디버그 화면

## 검증

PR 전 다음 검증을 수행한다.

```bash
cd client
flutter analyze
flutter test

cd ../packages/indoor_pdr_core
dart test
```

실기기 확인 항목:

1. iPhone과 Android에서 PDR 시작·anchor 선택·종료가 되는지
2. 보행 후 초록 경로가 graph 위에 표시되는지
3. JSON 공유창이 열리고 파일에 기기/anchor/경로/품질 정보가 있는지
4. 실제 알려진 거리와 확정 거리, 왕복 후 방향·누적 드리프트를 비교하는지

## 알려진 한계

- Android는 iOS `CMPedometer`처럼 OS가 추정한 거리를 직접 주지 않는다. 현재는
  `STEP_COUNTER`를 확정 걸음 기준으로 쓰고, 보폭은 보행 패턴 기반 추정치다.
- 맵매칭은 그래프가 정확하고 anchor가 맞을 때 효과적이다. 그래프가 실제 통로와
  다르면 위치를 잘못된 edge로 스냅할 수 있다.
- 거리·heading 품질은 기기·휴대 위치·보행 방식·자기장 환경에 따라 달라진다.
  따라서 더현대 현장 실측 JSON을 통한 후속 보정이 필요하다.
