import 'package:flutter/material.dart';

import '../../core/widgets/placeholder_panel.dart';

class RiskPage extends StatelessWidget {
  const RiskPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Risk')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          PlaceholderPanel(
            title: 'Deterministic Risk Engine',
            message:
                'Exposure, daily loss, drawdown, trade frequency, and risk/reward '
                'validation are computed by the deterministic RiskManager in '
                'Phase 6. Every proposal must be approved before an order can '
                'exist.',
            phase: 'Phase 6',
            icon: Icons.gpp_maybe_outlined,
          ),
        ],
      ),
    );
  }
}
