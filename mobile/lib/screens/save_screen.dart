import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../models/item.dart';
import '../services/api_client.dart';
import '../widgets/folder_badge.dart';

/// Shown when a URL arrives from the share sheet. Sends it to the backend and
/// reports what came back. Deliberately plain — visual polish is Phase 3.
class SaveScreen extends StatefulWidget {
  final String url;

  const SaveScreen({super.key, required this.url});

  @override
  State<SaveScreen> createState() => _SaveScreenState();
}

class _SaveScreenState extends State<SaveScreen> {
  late Future<Item> _saveFuture;

  @override
  void initState() {
    super.initState();
    _saveFuture = saveItem(widget.url);
  }

  // Re-assigning the Future inside setState is what makes FutureBuilder run
  // again — it rebuilds and sees a Future it hasn't subscribed to yet.
  void _retry() {
    setState(() {
      _saveFuture = saveItem(widget.url);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Save')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: FutureBuilder<Item>(
          future: _saveFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return _Saving(url: widget.url);
            }
            if (snapshot.hasError) {
              return _SaveFailed(error: snapshot.error, onRetry: _retry);
            }
            return _SaveSucceeded(item: snapshot.data!);
          },
        ),
      ),
    );
  }
}

class _Saving extends StatelessWidget {
  final String url;

  const _Saving({required this.url});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const CircularProgressIndicator(),
        const SizedBox(height: 24),
        const Text('Saving...'),
        const SizedBox(height: 8),
        Text(
          url,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
      ],
    );
  }
}

class _SaveFailed extends StatelessWidget {
  final Object? error;
  final VoidCallback onRetry;

  const _SaveFailed({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        const Text("Couldn't save this link."),
        const SizedBox(height: 8),
        Text(
          '$error',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 24),
        FilledButton(onPressed: onRetry, child: const Text('Retry')),
      ],
    );
  }
}

class _SaveSucceeded extends StatelessWidget {
  final Item item;

  const _SaveSucceeded({required this.item});

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        FolderBadge(folder: item.folder),
        const SizedBox(height: 16),
        Text(item.title, style: Theme.of(context).textTheme.titleLarge),
        if (item.summary != null) ...[
          const SizedBox(height: 8),
          Text(item.summary!),
        ],
        // The backend still saves when the AI can't run, using placeholder
        // text. Saying so is more honest than showing "Untitled saved item"
        // as if it were a real title — and the two reasons need different
        // wording, because only one of them is the user's problem to wait out.
        if (item.aiStatus == 'quota_exceeded') ...[
          const SizedBox(height: 16),
          _Notice(
            icon: Icons.hourglass_empty,
            text: "Your link is saved. Today's AI limit has been reached, so "
                'the title and folder will stay blank until it resets.',
          ),
        ] else if (item.aiStatus == 'failed') ...[
          const SizedBox(height: 16),
          _Notice(
            icon: Icons.info_outline,
            text: 'Saved, but AI details are unavailable for this link.',
          ),
        ],
        const SizedBox(height: 32),
        Center(
          child: FilledButton(
            // Closes Fetch and returns the user to whatever app they shared
            // from — the natural end of a share flow.
            onPressed: () => SystemNavigator.pop(),
            child: const Text('Done'),
          ),
        ),
      ],
    );
  }
}

/// A quiet icon + text line explaining why the AI details are missing. Muted
/// on purpose: the save itself succeeded, so this is an aside, not an error.
class _Notice extends StatelessWidget {
  final IconData icon;
  final String text;

  const _Notice({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(context).textTheme.bodySmall;

    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 16, color: style?.color),
        const SizedBox(width: 8),
        // Expanded, or a long message overflows the row instead of wrapping.
        Expanded(child: Text(text, style: style)),
      ],
    );
  }
}
