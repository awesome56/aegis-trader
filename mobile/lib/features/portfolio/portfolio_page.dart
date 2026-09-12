import 'package:flutter/material.dart';

import '../../core/widgets/placeholder_panel.dart';
import '../../core/widgets/stat_tile.dart';

class PortfolioPage extends StatelessWidget {
  const PortfolioPage({super.key});

  static const title = 'Portfolio';

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text(title),
        actions: const [
          IconButton(
            onPressed: null,
            icon: Icon(Icons.filter_list),
            tooltip: 'Range filters (1D/1W/1M/3M/1Y/ALL) arrive in Phase 4',
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          Row(
            children: [
              Expanded(
                child: StatTile(label: 'Total Value', value: '--'),
              ),
              SizedBox(width: 12),
              Expanded(
                child: StatTile(label: 'Daily Return', value: '--'),
              ),
            ],
          ),
          SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: StatTile(label: 'Total Return', value: '--'),
              ),
              SizedBox(width: 12),
              Expanded(
                child: StatTile(label: 'Cash', value: '--'),
              ),
            ],
          ),
          SizedBox(height: 24),
          SectionHeader(title: 'Allocation'),
          PlaceholderPanel(
            title: 'Asset allocation',
            message:
                'Allocation and equity-history charts render once the Portfolio '
                'Service and snapshots are available.',
            phase: 'Phase 4',
            icon: Icons.donut_large_outlined,
          ),
          SizedBox(height: 16),
          SectionHeader(title: 'Positions'),
          PlaceholderPanel(
            title: 'Position list',
            message:
                'Average entry, weight, unrealized/realized P&L and the '
                'position-detail drill-down are delivered in Phase 4.',
            phase: 'Phase 4',
            icon: Icons.list_alt_outlined,
          ),
        ],
      ),
    );
  }
}
