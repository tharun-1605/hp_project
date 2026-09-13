import 'package:flutter_test/flutter_test.dart';
import 'package:mobile_app/main.dart';

void main() {
  testWidgets('VisionNav app renders main title', (WidgetTester tester) async {
    await tester.pumpWidget(const VisionNavApp());
    expect(find.text('VisionNav'), findsOneWidget);
  });
}
