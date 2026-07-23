import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:receive_sharing_intent/receive_sharing_intent.dart';

/// Wraps `receive_sharing_intent` and exposes just the URL/text string Fetch
/// cares about — callers don't need to know about [SharedMediaFile].
class ShareIntentService {
  StreamSubscription<List<SharedMediaFile>>? _subscription;

  /// The URL the app was launched with via the share sheet (cold start).
  /// Returns null if the app wasn't opened via a share, or if the platform
  /// channel isn't available (e.g. running in a widget test).
  Future<String?> getInitialSharedUrl() async {
    try {
      final files = await ReceiveSharingIntent.instance.getInitialMedia();
      if (files.isEmpty) return null;
      // Tell the plugin we've consumed this, so it isn't redelivered.
      await ReceiveSharingIntent.instance.reset();
      return files.first.path;
    } catch (e) {
      debugPrint('ShareIntentService.getInitialSharedUrl failed: $e');
      return null;
    }
  }

  /// Listens for shares that arrive while the app is already running.
  void listen(void Function(String url) onSharedUrl) {
    _subscription = ReceiveSharingIntent.instance.getMediaStream().listen(
      (files) {
        if (files.isNotEmpty) onSharedUrl(files.first.path);
      },
      onError: (Object e) => debugPrint('ShareIntentService stream error: $e'),
    );
  }

  void dispose() {
    _subscription?.cancel();
  }
}
