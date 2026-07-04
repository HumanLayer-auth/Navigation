import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:navigation_client/widgets/location_marker.dart';
import 'package:navigation_client/widgets/status_badge.dart';
import 'package:navigation_client/widgets/uncertainty_circle.dart';

void main() {
  testWidgets('LocationMarker uses the outdoor mode color by default', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: LocationMarker(mode: LocationMode.outdoor),
      ),
    );

    final icon = tester.widget<Icon>(find.byType(Icon));
    expect(icon.icon, Icons.navigation);
    expect(icon.color, Colors.blue);
  });

  testWidgets('LocationMarker colorOverride wins over the mode color', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: LocationMarker(
          mode: LocationMode.outdoor,
          colorOverride: Colors.amber,
        ),
      ),
    );

    final icon = tester.widget<Icon>(find.byType(Icon));
    expect(icon.color, Colors.amber);
  });

  testWidgets('UncertaintyCircle renders with the requested diameter', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: UncertaintyCircle(diameter: 40, color: Colors.purple),
      ),
    );

    final box = tester.widget<SizedBox>(find.byType(SizedBox));
    expect(box.width, 40);
    expect(box.height, 40);
  });

  testWidgets('StatusBadge shows the given label', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: StatusBadge(label: 'GPS 신호 약함'),
      ),
    );

    expect(find.text('GPS 신호 약함'), findsOneWidget);
  });
}
