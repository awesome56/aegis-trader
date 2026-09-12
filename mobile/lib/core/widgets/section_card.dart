import 'package:flutter/material.dart';

/// Card with a section title used across settings/info screens.
class SectionCard extends StatelessWidget {
  const SectionCard({super.key, required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(4, 0, 4, 8),
          child: Text(title, style: Theme.of(context).textTheme.titleMedium),
        ),
        Card(child: child),
      ],
    );
  }
}
