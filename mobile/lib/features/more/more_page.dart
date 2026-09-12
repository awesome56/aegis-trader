import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../providers/auth_provider.dart';

class MorePage extends ConsumerWidget {
  const MorePage({super.key});

  static const title = 'More';

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text(title)),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.shield_outlined),
            title: const Text('Risk'),
            subtitle: const Text('Exposure, limits, drawdown, alerts'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/more/risk'),
          ),
          ListTile(
            leading: const Icon(Icons.science_outlined),
            title: const Text('Backtests'),
            subtitle: const Text('Strategy performance and equity curves'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/more/backtests'),
          ),
          ListTile(
            leading: const Icon(Icons.notifications_outlined),
            title: const Text('Notifications'),
            subtitle: const Text('Risk alerts and trade events'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/more/notifications'),
          ),
          ListTile(
            leading: const Icon(Icons.settings_outlined),
            title: const Text('Settings'),
            subtitle: const Text('System status, appearance, account'),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => context.go('/more/settings'),
          ),
          const Divider(),
          ListTile(
            leading: Icon(
              auth.isAuthenticated ? Icons.person : Icons.login,
              color: auth.isAuthenticated
                  ? Theme.of(context).colorScheme.primary
                  : null,
            ),
            title: Text(auth.isAuthenticated ? 'Signed in' : 'Signed out'),
            subtitle: Text(auth.user?.email ?? 'Authentication is required for protected data'),
          ),
        ],
      ),
    );
  }
}
