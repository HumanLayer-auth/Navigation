# M4-002 · Particle Filter 지도 매칭 baseline

- **상태**: Draft
- **마일스톤**: M4 · 지도 매칭과 실시간 내비게이션
- **권장 진행**: 4주차 중반
- **컴포넌트**: pdr / routing
- **GitHub**: -
- **선행 이슈**: M2-001, M3-003

## 설명

PDR 단독은 시간이 지날수록 오차가 누적된다. 이 이슈는 평면도의 벽 제약을 이용해 벽을 통과하는
particle을 제거하고, 살아남은 particle의 평균으로 현재 위치와 불확실성을 추정하는 baseline을 만든다.

이 기능이 프로젝트의 기술적 핵심이다. 처음부터 고성능 최적화까지 가지 않고, 작은 샘플 평면도에서
동작이 보이는 구조를 먼저 만든다.

## 작업 내용

### 1. 평면도 제약 자료구조

- M2-001의 `wall` Feature를 벽 선분 목록으로 변환한다.
- 보행 가능 영역 또는 복도 영역을 확인할 수 있는 구조를 준비한다.
- 선분 교차 판정 유틸을 만든다.

### 2. Particle Filter 구현

- particle 상태를 `x`, `y`, `heading`, `weight`로 표현한다.
- 실내 전환 시 입구 주변에 particle을 초기화한다.
- PDR step마다 prediction을 수행한다.
- 이전 위치와 새 위치 사이 선분이 벽을 통과하면 weight를 낮추거나 0으로 둔다.
- low-variance 또는 systematic resampling을 구현한다.

### 3. 위치/불확실성 산출

- 살아남은 particle의 가중 평균을 현재 위치로 반환한다.
- particle 분산을 불확실성 원 크기로 변환한다.
- particle이 너무 적게 살아남으면 재초기화 또는 경고 상태를 반환한다.

### 4. 시각화

- 개발 모드에서 particle cloud를 켜고 끌 수 있게 한다.
- 기본 화면에는 보정된 현재 위치와 불확실성 원만 표시한다.

## 수용 기준

- 더미 평면도에서 벽을 통과하는 particle이 제거된다.
- PDR 단독 위치와 PF 보정 위치를 구분해 확인할 수 있다.
- 현재 위치와 불확실성 값이 지도 화면으로 전달된다.
- 작은 mock 경로에 대한 단위 테스트가 있다.

## 검증

```powershell
cd client
flutter analyze
flutter test
flutter run
```

## 범위 밖

- 고급 공간 인덱싱 최적화
- 문 통과 감지
- 실측 정확도 리포트
- 다층 Particle Filter
