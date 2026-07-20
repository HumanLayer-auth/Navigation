import 'package:flutter/material.dart';

import 'features/indoor_navigation/application/indoor_navigation_controller.dart';
import 'features/indoor_navigation/debug/pdr_device_harness.dart';
import 'features/indoor_navigation/platform/ios_pdr_motion_source.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  final source = IosPdrMotionSource();
  final driver = IndoorNavigationDriver(source: source);
  runApp(
    MaterialApp(
      debugShowCheckedModeBanner: false,
      home: PdrDeviceHarness(source: source, driver: driver),
    ),
  );
}
