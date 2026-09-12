import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/stat_tile.dart';
import '../../core/widgets/state_views.dart';
import '../../models/system_status.dart';
import '../../repositories/system_repository.dart';

class DashboardPage extends ConsumerWidget {
  const DashboardPage({super.key});

  static const title = 'Dashboard';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(systemStatusProvider);

    return Scaffold(
      appBar: AppBar(title: const Text(title)),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(systemStatusProvider),
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _TradingStatusBanner(status: status),
            const SizedBox(height: 16),
            const _MetricGrid(),
            const SizedBox(height: 24),
            const SectionHeader(title: 'Open Positions'),
            const SizedBox(height: 200),
            const Card(
              child: EmptyState(
                icon: Icons.account_balance_wallet_outlined,
                title: 'No positions yet',
                message:
                    'Live position tracking is delivered in Phase 4 with the '
                    'Portfolio Service.',
              ),
            ),
            const SizedBox(height: 24),
            const SectionHeader(title: 'Recent Agent Decisions'),
            const Card(
              child: EmptyState(
                icon: Icons.smart_toy_outlined,
                title: 'Agent not connected',
                message:
                    'The TradingAnalysisAgent arrives in Phase 9. Only concise '
                    'decision evidence will be shown here (never hidden '
                    'chain-of-thought).',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _MetricGrid extends StatelessWidget {
  const _MetricGrid();

  @override
  Widget build(BuildContext context) {
    return const Column(
      children: [
        Row(
          children: [
            Expanded(child: StatTile(label: 'Portfolio Value', value: '--')),
            SizedBox(width: 12),
            Expanded(child: StatTile(label: "Today's P&L", value: '--')),
          ],
        ),
        SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: StatTile(label: 'Total Return', value: '--')),
            SizedBox(width: 12),
            Expanded(child: StatTile(label: 'Buying Power', value: '--')),
          ],
        ),
      ],
    );
  }
}

class _TradingStatusBanner extends StatelessWidget {
  const _TradingStatusBanner({required this.status});

  final AsyncValue<SystemStatus> status;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return status.when(
      loading: () => const Card(
        child: ListTile(
          leading: SizedBox(
            width: 20,
            height: 20,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
          title: Text('Connecting to backend...'),
        ),
      ),
      error: (error, _) => Card(
        child: ListTile(
          leading: Icon(Icons.cloud_off, color: theme.colorScheme.error),
          title: const Text('Backend unreachable'),
          subtitle: const Text('Start the API and pull down to retry.'),
        ),
      ),
      data: (value) {
        final color = value.isEmergencyStopped
            ? AppTheme.negative
            : (value.isPaperTrading ? AppTheme.positive : AppTheme.warning);
        return Card(
          child: ListTile(
            leading: Icon(Icons.shield_outlined, color: color),
            title: Text(
              value.isPaperTrading ? 'Paper Trading Active' : 'Live Trading',
              style: theme.textTheme.titleMedium,
            ),
            subtitle: Text(
              'Broker: ${value.brokerProvider}  •  '
              'Market data: ${value.marketDataProvider}  •  '
              'Kill switch: ${value.killSwitchState}',
            ),
          ),
        );
      },
    );
  }
}
