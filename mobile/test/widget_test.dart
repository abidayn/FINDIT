import 'package:flutter_test/flutter_test.dart';

import 'package:mobile/main.dart';

void main() {
  testWidgets('Home screen shows the app name', (WidgetTester tester) async {
    await tester.pumpWidget(const StashApp());

    expect(find.text('Stash'), findsOneWidget);
  });
}
