import 'package:flutter/material.dart';

import '../../core/widgets/placeholder_panel.dart';

class NotificationsPage extends StatelessWidget {
  const NotificationsPage({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notifications')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: const [
          PlaceholderPanel(
            title: 'Notification center',
            message:
                'Trade executions, risk warnings, broker/market-data '
                'disconnects, and emergency-stop events will be listed here '
                'once notification dispatch lands in Phase 4.',
            phase: 'Phase 4',
            icon: Icons.notifications_outlined,
          ),
        ],
      ),
    );
  }
}
