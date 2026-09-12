import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/theme/app_theme.dart';
import '../../core/widgets/section_card.dart';
import '../../providers/auth_provider.dart';
import '../../providers/theme_provider.dart';
import '../../repositories/system_repository.dart';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final themeMode = ref.watch(themeModeProvider);
    final status = ref.watch(systemStatusProvider);
    final health = ref.watch(healthProvider);
    final auth = ref.watch(authControllerProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          SectionCard(
            title: 'Trading',
            child: status.when(
              loading: () => const ListTile(title: Text('Loading...')),
              error: (error, _) => ListTile(
                title: const Text('Unavailable'),
                subtitle: Text(error.toString()),
              ),
              data: (value) => Column(
                children: [
                  ListTile(
                    title: const Text('Mode'),
                    trailing: _Chip(
                      label: value.tradingMode.toUpperCase(),
                      color: value.isPaperTrading
                          ? AppTheme.positive
                          : AppTheme.warning,
                    ),
                  ),
                  ListTile(
                    title: const Text('Kill switch'),
                    trailing: _Chip(
                      label: value.killSwitchState,
                      color: value.isEmergencyStopped
                          ? AppTheme.negative
                          : AppTheme.positive,
                    ),
                  ),
                  ListTile(
                    title: const Text('Live trading'),
                    subtitle: Text(
                      value.liveTradingGuard.allowed
                          ? 'All interlock conditions satisfied'
                          : 'Blocked (${value.liveTradingGuard.missingRequirements.length} '
                              'requirements missing)',
                    ),
                    trailing: Icon(
                      value.liveTradingGuard.allowed
                          ? Icons.lock_open
                          : Icons.lock,
                      color: value.liveTradingGuard.allowed
                          ? AppTheme.negative
                          : AppTheme.positive,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'System Health',
            child: health.when(
              loading: () => const ListTile(title: Text('Checking...')),
              error: (error, _) => ListTile(
                title: const Text('Backend unreachable'),
                subtitle: Text(error.toString()),
                trailing: IconButton(
                  icon: const Icon(Icons.refresh),
                  onPressed: () => ref.invalidate(healthProvider),
                ),
              ),
              data: (value) => Column(
                children: [
                  ListTile(
                    title: const Text('Overall'),
                    subtitle: Text('v${value.version} • ${value.environment}'),
                    trailing: _Chip(
                      label: value.status.toUpperCase(),
                      color: value.status == 'healthy'
                          ? AppTheme.positive
                          : AppTheme.warning,
                    ),
                  ),
                  for (final component in value.components)
                    ListTile(
                      dense: true,
                      title: Text(component.name),
                      subtitle: component.latencyMs == null
                          ? null
                          : Text('${component.latencyMs!.toStringAsFixed(1)} ms'),
                      trailing: Icon(
                        component.isHealthy
                            ? Icons.check_circle_outline
                            : Icons.error_outline,
                        color:
                            component.isHealthy ? AppTheme.positive : AppTheme.negative,
                      ),
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Appearance',
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: SegmentedButton<ThemeMode>(
                segments: const [
                  ButtonSegment(
                    value: ThemeMode.system,
                    label: Text('System'),
                    icon: Icon(Icons.brightness_auto),
                  ),
                  ButtonSegment(
                    value: ThemeMode.light,
                    label: Text('Light'),
                    icon: Icon(Icons.light_mode),
                  ),
                  ButtonSegment(
                    value: ThemeMode.dark,
                    label: Text('Dark'),
                    icon: Icon(Icons.dark_mode),
                  ),
                ],
                selected: {themeMode},
                onSelectionChanged: (selection) =>
                    ref.read(themeModeProvider.notifier).setMode(selection.first),
              ),
            ),
          ),
          const SizedBox(height: 16),
          SectionCard(
            title: 'Account',
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.person_outline),
                  title: Text(
                    auth.isAuthenticated
                        ? (auth.user?.email ?? 'Signed in')
                        : 'Not signed in',
                  ),
                  subtitle: Text(
                    auth.isAuthenticated
                        ? 'Session active'
                        : 'Sign in to access protected data',
                  ),
                ),
                Padding(
                  padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
                  child: SizedBox(
                    width: double.infinity,
                    child: auth.isAuthenticated
                        ? OutlinedButton.icon(
                            onPressed: () =>
                                ref.read(authControllerProvider.notifier).logout(),
                            icon: const Icon(Icons.logout),
                            label: const Text('Sign out'),
                          )
                        : FilledButton.icon(
                            onPressed: () => context.go('/login'),
                            icon: const Icon(Icons.login),
                            label: const Text('Sign in'),
                          ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Chip extends StatelessWidget {
  const _Chip({required this.label, required this.color});

  final String label;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.15),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(color: color),
      ),
    );
  }
}
