import 'package:aegis_trader_mobile/core/widgets/placeholder_panel.dart';
import 'package:aegis_trader_mobile/core/widgets/state_views.dart';
import 'package:aegis_trader_mobile/core/widgets/stat_tile.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('StatTile renders its label and value', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: StatTile(label: 'Portfolio Value', value: '--'),
        ),
      ),
    );

    expect(find.text('Portfolio Value'), findsOneWidget);
    expect(find.text('--'), findsOneWidget);
  });

  testWidgets('EmptyState renders title and message', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: EmptyState(title: 'No positions yet', message: 'Coming soon'),
        ),
      ),
    );

    expect(find.text('No positions yet'), findsOneWidget);
    expect(find.text('Coming soon'), findsOneWidget);
  });

  testWidgets('PlaceholderPanel shows the delivery phase', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: PlaceholderPanel(
            title: 'Market data',
            message: 'Delivered later',
            phase: 'Phase 2',
          ),
        ),
      ),
    );

    expect(find.text('Market data'), findsOneWidget);
    expect(find.text('Phase 2'), findsOneWidget);
  });

  testWidgets('ErrorView triggers retry callback', (tester) async {
    var retried = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: ErrorView(
            message: 'Backend unreachable',
            onRetry: () => retried = true,
          ),
        ),
      ),
    );

    await tester.tap(find.text('Retry'));
    expect(retried, isTrue);
  });
}
