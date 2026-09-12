import 'package:flutter/material.dart';

import '../../core/widgets/placeholder_panel.dart';

class BacktestsPage extends StatelessWidget {
  const BacktestsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Backtests')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          PlaceholderPanel(
            title: 'Backtesting engine',
            message:
                'Configure strategy, assets, timeframe, balance and date range, '
                'then review return, drawdown, Sharpe, win rate, profit factor '
                'and the equity curve. Delivered in Phase 8 using the same '
                'strategy implementations as live trading.',
            phase: 'Phase 8',
            icon: Icons.science_outlined,
          ),
        ],
      ),
    );
  }
}
