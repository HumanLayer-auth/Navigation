import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:navigation_client/app.dart';

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();

  testWidgets('메인 앱 루트가 생성된다', (tester) async {
    await tester.pumpWidget(const NavigationApp());

    expect(find.byType(NavigationApp), findsOneWidget);
  });
}
