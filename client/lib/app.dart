import 'dart:async';

import 'package:flutter/material.dart';

import 'core/service_locator.dart';
import 'core/theme/app_theme.dart';
import 'routing/app_routes.dart';
import 'screens/arrival/arrival_screen.dart';
import 'screens/debug/api_health_check_screen.dart';
import 'screens/debug/floor_map_preview_screen.dart';
import 'screens/debug/pdr_svg_test_screen.dart';
import 'screens/destination/destination_screen.dart';
import 'screens/indoor_map/indoor_map_screen.dart';
import 'screens/outdoor_map/outdoor_map_screen.dart';
import 'screens/route_guide/route_guide_screen.dart';
import 'screens/splash/splash_screen.dart';

void defaultPdrBackgrounded() {
  unawaited(indoorNavigationDriver.onAppBackgrounded());
}

void defaultPdrForegrounded() {
  unawaited(indoorNavigationDriver.onAppForegrounded());
}

class NavigationApp extends StatefulWidget {
  const NavigationApp({
    super.key,
    this.onPdrBackgrounded = defaultPdrBackgrounded,
    this.onPdrForegrounded = defaultPdrForegrounded,
  });

  final VoidCallback onPdrBackgrounded;
  final VoidCallback onPdrForegrounded;

  @override
  State<NavigationApp> createState() => _NavigationAppState();
}

class _NavigationAppState extends State<NavigationApp>
    with WidgetsBindingObserver {
  bool _pdrBackgrounded = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      if (!_pdrBackgrounded) return;
      _pdrBackgrounded = false;
      widget.onPdrForegrounded();
      return;
    }
    if (_pdrBackgrounded) return;
    _pdrBackgrounded = true;
    widget.onPdrBackgrounded();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Navigation Client',
      theme: buildAppTheme(),
      initialRoute: AppRoutes.splash,
      routes: {
        AppRoutes.splash: (context) => const SplashScreen(),
        AppRoutes.outdoorMap: (context) => const OutdoorMapScreen(),
        AppRoutes.indoorMap: (context) => const IndoorMapScreen(),
        AppRoutes.destination: (context) => const DestinationScreen(),
        AppRoutes.routeGuide: (context) => const RouteGuideScreen(),
        AppRoutes.arrival: (context) => const ArrivalScreen(),
        AppRoutes.debugApiHealth: (context) => const ApiHealthCheckScreen(),
        AppRoutes.debugFloorMapPreview: (context) =>
            const FloorMapPreviewScreen(),
        AppRoutes.pdrSvgTest: (context) => const PdrSvgTestScreen(),
      },
    );
  }
}
