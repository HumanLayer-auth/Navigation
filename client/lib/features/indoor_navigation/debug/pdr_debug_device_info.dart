import 'package:device_info_plus/device_info_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:package_info_plus/package_info_plus.dart';

/// 세션 비교에 필요한 최소 기기/빌드 식별자. 권한·개인 위치 정보는 수집하지 않는다.
class PdrDebugDeviceInfo {
  const PdrDebugDeviceInfo._();

  static Future<Map<String, Object?>> load() async {
    final info = <String, Object?>{'platform': defaultTargetPlatform.name};
    try {
      final package = await PackageInfo.fromPlatform();
      info.addAll({
        'app_version': package.version,
        'app_build': package.buildNumber,
      });
    } on Object {
      // 공유 자체는 앱 메타데이터 조회 실패와 무관하게 가능해야 한다.
    }

    try {
      final plugin = DeviceInfoPlugin();
      if (defaultTargetPlatform == TargetPlatform.android) {
        final android = await plugin.androidInfo;
        info.addAll({
          'device_name': '${android.manufacturer} ${android.model}',
          'os_version': android.version.release,
          'sdk_int': android.version.sdkInt,
        });
      } else if (defaultTargetPlatform == TargetPlatform.iOS) {
        final ios = await plugin.iosInfo;
        info.addAll({
          'device_name': ios.name,
          'model': ios.model,
          'os_version': ios.systemVersion,
        });
      }
    } on Object {
      // emulator/플러그인 초기화 실패 때도 export는 유지한다.
    }
    return info;
  }
}
