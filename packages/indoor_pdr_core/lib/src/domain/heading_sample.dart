/// 늦게 도착한 CMPedometer batch를 해당 시각의 heading으로 재구성하기 위한 샘플.
///
/// [yawDeg]/[deviceHeadingDeg]는 경로 계산에 쓰지 않는 진단용이다. fused(자북 기준)
/// heading이 공간 이동 중 실제로 얼마나 흘렀는지 비교하려고 함께 보관한다.
///
/// 연구 앱 `pdr_types.dart`의 `HeadingSample` typedef를 값 클래스로 옮겼다.
class HeadingSample {
  const HeadingSample({
    required this.ms,
    required this.walkDeg,
    required this.fusedDeg,
    required this.yawDeg,
    required this.deviceHeadingDeg,
  });

  final int ms;
  final double walkDeg;
  final double fusedDeg;
  final double yawDeg;
  final double deviceHeadingDeg;
}
