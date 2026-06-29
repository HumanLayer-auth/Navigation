# M3-003 · Heading 추정과 PDR 엔진 통합

- **상태**: Draft
- **마일스톤**: M3 · 센서 수집과 PDR 기본 동작
- **권장 진행**: 3주차 후반
- **컴포넌트**: pdr / navigation
- **GitHub**: -
- **선행 이슈**: M3-001, M3-002

## 설명

걸음과 보폭만으로는 위치를 계산할 수 없다. 어느 방향으로 이동했는지를 나타내는 heading이 필요하다.
이 이슈는 자이로와 지자기 값을 이용해 heading baseline을 만들고, M3-002의 step/stride와 합쳐
PDR 위치 추정 엔진을 완성한다.

M3의 결과물은 "지도 매칭 전의 순수 PDR 경로"다. 벽을 통과하거나 조금씩 드리프트가 생겨도 괜찮다.
그 한계를 M4의 Particle Filter가 보정한다.

## 작업 내용

### 1. Heading baseline

- 자이로 적분 기반 상대 회전값을 계산한다.
- 지자기 또는 플랫폼 heading 값을 이용해 드리프트를 보정한다.
- 처음에는 complementary filter 수준으로 단순하게 시작한다.

### 2. PDR 엔진 통합

- `step_detector`, `stride_estimator`, `heading_filter`를 `pdr_engine`에서 합친다.
- 초기 위치 `(x, y, floor)`와 초기 heading을 입력받는다.
- step event마다 새 위치 추정값을 반환한다.

### 3. 지도 화면 연결

- 개발 모드에서 더미 평면도 위에 PDR 위치 마커를 움직인다.
- PDR 단독 결과임을 구분할 수 있도록 상태 배지 또는 로그를 둔다.

### 4. 로그 재생

- 센서 로그를 간단한 JSON/CSV로 저장하거나 mock stream으로 재생할 수 있게 한다.
- 같은 로그를 여러 번 돌려 결과를 비교할 수 있게 한다.

## 수용 기준

- PDR 엔진이 초기 위치와 센서 이벤트를 받아 연속 위치 추정값을 만든다.
- 실기기 또는 mock stream에서 마커가 이동한다.
- PDR 단독 경로 로그를 저장하거나 재생할 수 있다.
- heading 관련 파라미터가 문서화되어 있다.

## 검증

```powershell
cd client
flutter analyze
flutter test
flutter run
```

## 범위 밖

- 벽 제약 보정
- 자동 실내 진입 감지
- 정확도 목표 달성 튜닝
- 경로 이탈 재탐색
