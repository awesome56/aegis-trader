import 'package:flutter/material.dart';

import '../../core/widgets/placeholder_panel.dart';

class MarketsPage extends StatelessWidget {
  const MarketsPage({super.key});

  static const title = 'Markets';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          TextField(
            enabled: false,
            decoration: InputDecoration(
              prefixIcon: Icon(Icons.search),
              hintText: 'Search symbols (available in Phase 2)',
            ),
          ),
          SizedBox(height: 16),
          PlaceholderPanel(
            title: 'Market data',
            message:
                'Quotes, candles, and watchlists require the MarketDataProvider '
                'abstraction introduced in Phase 2. No synthetic prices are '
                'shown intentionally.',
            phase: 'Phase 2',
            icon: Icons.show_chart_outlined,
          ),
        ],
      ),
    );
  }
}
