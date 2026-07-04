import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:navigation_client/app.dart';
import 'package:navigation_client/core/service_locator.dart';
import 'package:navigation_client/screens/debug/api_health_check_screen.dart';
import 'package:navigation_client/screens/indoor_map/indoor_map_screen.dart';

void main() {
  setUp(() {
    // 실제 permission_handler 플러그인 채널이 없는 테스트 환경에서 멈추지 않도록
    // 즉시 완료되는 가짜 권한 요청으로 교체한다.
    requestStartupPermissions = () async => {};
  });

  tearDown(() {
    requestStartupPermissions = defaultRequestStartupPermissions;
  });

  testWidgets('splash screen shows entry points', (WidgetTester tester) async {
    await tester.pumpWidget(const NavigationApp());

    expect(find.text('Navigation'), findsOneWidget);
    expect(find.text('시작하기'), findsOneWidget);
  });

  testWidgets('splash screen requests permissions then stops loading', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const NavigationApp());

    expect(find.byType(LinearProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();

    expect(find.byType(LinearProgressIndicator), findsNothing);
  });

  testWidgets('splash "시작하기" navigates to outdoor map', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const NavigationApp());

    await tester.tap(find.text('시작하기'));
    await tester.pumpAndSettle();

    expect(find.text('야외 지도 (GPS 모드)'), findsOneWidget);
  });

  testWidgets('api health check shows loading then a status message', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(home: ApiHealthCheckScreen()),
    );

    // Right after start, the health check is in-flight.
    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    // The http call will fail immediately in the widget-test environment
    // (no real network), so let it settle and show a status message.
    await tester.pumpAndSettle(const Duration(seconds: 6));

    expect(find.byType(CircularProgressIndicator), findsNothing);
    expect(find.byIcon(Icons.refresh), findsOneWidget);
  });

  testWidgets('indoor map shows building info loaded from the repository', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const MaterialApp(home: IndoorMapScreen()));

    expect(find.byType(CircularProgressIndicator), findsOneWidget);

    await tester.pumpAndSettle();

    expect(find.textContaining('데모 건물'), findsOneWidget);
  });
}
