import 'package:flutter/material.dart';

/// Placeholder screen for task 1.8 (share intent integration) — it only
/// proves a shared URL made it from the Android share sheet into the app.
/// Task 1.9 replaces this body with the real save flow (POST /save,
/// loading/success/error states).
class SaveScreen extends StatelessWidget {
  final String url;

  const SaveScreen({super.key, required this.url});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Save')),
      body: Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text('Received shared URL:\n$url', textAlign: TextAlign.center),
        ),
      ),
    );
  }
}
