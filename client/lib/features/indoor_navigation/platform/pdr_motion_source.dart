import 'native_pdr_event.dart';

/// PDR 센서 이벤트의 플랫폼 중립 경계.
///
/// 연구 앱 `MotionSource`의 typed 승격판. iOS/Android 구현이나 테스트 fake는 이
/// 인터페이스 뒤에 숨는다. 컨트롤러/코어는 어느 플랫폼이 raw 이벤트를 만들었는지
/// 모른다. GPS/IMUv3/JSON export는 이식 범위에서 제외했다.
abstract interface class PdrMotionSource {
  /// 파싱된 센서 이벤트 스트림.
  Stream<NativePdrEvent> get events;

  /// 센서 스트림 시작.
  Future<void> start();

  /// 센서 스트림 정지.
  Future<void> stop();

  /// CMPedometer를 "지금"부터 재시작한다. 새 stepSessionId를 반환한다.
  Future<int?> resetPedometer();

  /// 리소스 해제.
  Future<void> dispose();
}
