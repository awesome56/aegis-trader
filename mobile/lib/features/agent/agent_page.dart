import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/widgets/placeholder_panel.dart';
import '../../repositories/system_repository.dart';

class AgentPage extends ConsumerWidget {
  const AgentPage({super.key});

  static const title = 'Agent';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = ref.watch(systemStatusProvider);
    final enabled = status.valueOrNull?.agentEnabled ?? false;

    return Scaffold(
      appBar: AppBar(title: const Text(title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: ListTile(
              leading: Icon(
                enabled ? Icons.smart_toy : Icons.smart_toy_outlined,
                color: enabled
                    ? Theme.of(context).colorScheme.primary
                    : Theme.of(context).colorScheme.outline,
              ),
              title: Text(enabled ? 'Agent enabled' : 'Agent disabled'),
              subtitle: const Text(
                'The agent can only create trade proposals; it can never submit '
                'orders or bypass the Risk Engine.',
              ),
            ),
          ),
          const SizedBox(height: 16),
          const PlaceholderPanel(
            title: 'Agent activity',
            message:
                'Decision summaries, proposals, rejected proposals, confidence '
                'and supporting strategy signals appear here in Phase 9. Hidden '
                'chain-of-thought is never stored or displayed.',
            phase: 'Phase 9',
            icon: Icons.psychology_outlined,
          ),
        ],
      ),
    );
  }
}
