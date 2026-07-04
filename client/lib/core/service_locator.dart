import 'package:permission_handler/permission_handler.dart';

import '../repositories/building_repository.dart';
import '../repositories/mock_building_repository.dart';

/// 백엔드가 준비되면 이 한 줄만 [HttpBuildingRepository]로 바꾼다.
final BuildingRepository buildingRepository = MockBuildingRepository();

Future<Map<Permission, PermissionStatus>> defaultRequestStartupPermissions() {
  return [
    Permission.locationWhenInUse,
    Permission.activityRecognition,
  ].request();
}

/// 스플래시 화면의 시작 권한 요청. 플랫폼 채널이 없는 테스트 환경에서는
/// 이 변수를 즉시 완료되는 가짜 함수로 교체해 실제 플러그인 호출을 피한다.
Future<Map<Permission, PermissionStatus>> Function() requestStartupPermissions =
    defaultRequestStartupPermissions;
