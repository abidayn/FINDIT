import 'package:flutter/material.dart';

import '../services/api_client.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late final Future<String> _healthStatus;

  @override
  void initState() {
    super.initState();
    _healthStatus = fetchHealth();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Text('Fetch', style: TextStyle(fontSize: 24)),
            const SizedBox(height: 16),
            FutureBuilder<String>(
              future: _healthStatus,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const CircularProgressIndicator();
                }
                if (snapshot.hasError) {
                  return Text('Backend unreachable: ${snapshot.error}');
                }
                return Text('Backend status: ${snapshot.data}');
              },
            ),
          ],
        ),
      ),
    );
  }
}
