# M3-002 · 걸음 감지와 보폭 추정 baseline

- **상태**: Draft
- **마일스톤**: M3 · 센서 수집과 PDR 기본 동작
- **권장 진행**: 3주차 중반
- **컴포넌트**: pdr
- **GitHub**: -
- **선행 이슈**: M3-001

## 설명

PDR의 첫 입력은 "몇 걸음을 걸었고, 한 걸음이 몇 미터인가"다.
이 이슈는 가속도 magnitude 기반 peak detection과 Weinberg 보폭 모델을 baseline으로 구현한다.

정확도는 M5에서 정량 평가한다. 여기서는 반복 테스트 가능한 구조와 과도한 false peak를 막는 기본
조건을 갖추는 것이 핵심이다.

## 작업 내용

### 1. 가속도 전처리

- 3축 가속도에서 magnitude를 계산한다.
- 간단한 low-pass filter 또는 moving average로 노이즈를 줄인다.
- 필터 파라미터를 상수로 분리한다.

### 2. 걸음 감지

- peak detection을 구현한다.
- 최소 걸음 간격 조건을 둔다.
- 임계값 이하의 흔들림은 걸음으로 세지 않는다.
- 개발 중 확인할 수 있도록 step event 로그를 남긴다.

### 3. 보폭 추정

- 1차는 고정 보폭 또는 사용자 키 기반 보폭을 제공한다.
- Weinberg 모델을 선택적으로 적용할 수 있게 한다.
- step event마다 추정 거리 값을 반환한다.

### 4. 테스트/재현

- mock acceleration sequence로 단위 테스트를 작성한다.
- 실제 보행 10m, 20m 같은 간단한 수동 테스트 절차를 문서화한다.

## 수용 기준

- mock 데이터에서 기대한 걸음 수가 계산된다.
- 실제 기기에서 걷기와 흔들기를 구분하는 최소 baseline이 동작한다.
- step event마다 stride estimate가 반환된다.
- 파라미터를 코드 한 곳에서 조정할 수 있다.

## 검증

```powershell
cd client
flutter analyze
flutter test
flutter run
```

## 범위 밖

- heading 추정
- 현재 위치 x/y 적분
- Particle Filter 보정
- 사용자별 보폭 자동 학습
