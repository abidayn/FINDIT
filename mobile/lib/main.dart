import 'package:flutter/material.dart';
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:go_router/go_router.dart';

import 'screens/home_screen.dart';
import 'screens/save_screen.dart';
import 'services/share_intent_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await dotenv.load(fileName: '.env');
  runApp(const FetchApp());
}

final _router = GoRouter(
  routes: [
    GoRoute(path: '/', builder: (context, state) => const HomeScreen()),
    GoRoute(
      path: '/save',
      builder: (context, state) => SaveScreen(url: state.extra as String),
    ),
  ],
);

class FetchApp extends StatefulWidget {
  const FetchApp({super.key});

  @override
  State<FetchApp> createState() => _FetchAppState();
}

class _FetchAppState extends State<FetchApp> {
  final _shareIntentService = ShareIntentService();

  @override
  void initState() {
    super.initState();

    // Cold start: the app was launched by tapping "Fetch" in the share sheet.
    _shareIntentService.getInitialSharedUrl().then((url) {
      if (url != null) _router.push('/save', extra: url);
    });

    // Warm start: the app was already open when a new share arrived.
    _shareIntentService.listen((url) => _router.push('/save', extra: url));
  }

  @override
  void dispose() {
    _shareIntentService.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Fetch',
      routerConfig: _router,
    );
  }
}
