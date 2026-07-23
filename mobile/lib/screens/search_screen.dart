import 'dart:async';

import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/item.dart';
import '../services/api_client.dart';
import '../widgets/item_card.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _controller = TextEditingController();

  Timer? _debounce;
  String _query = '';
  List<Item> _results = [];
  bool _loading = false;
  Object? _error;

  static const _debounceDelay = Duration(milliseconds: 300);

  @override
  void dispose() {
    // Both need cancelling: a pending timer would fire into a dead widget, and
    // the controller holds a native text-input connection.
    _debounce?.cancel();
    _controller.dispose();
    super.dispose();
  }

  /// Restarting the timer on every keystroke means only the last one in a
  /// 300ms window actually reaches the backend — otherwise "morning" would
  /// fire seven requests.
  void _onChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(_debounceDelay, () => _search(value));
  }

  Future<void> _search(String query) async {
    final trimmed = query.trim();
    setState(() {
      _query = trimmed;
      _loading = true;
      _error = null;
    });

    try {
      final results = trimmed.isEmpty ? <Item>[] : await searchItems(trimmed);
      // The field may have moved on while this request was in flight; ignore a
      // stale response so results never contradict what's typed.
      if (!mounted || trimmed != _controller.text.trim()) return;
      setState(() {
        _results = results;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e;
        _loading = false;
      });
    }
  }

  Future<void> _openItem(Item item) async {
    final uri = Uri.tryParse(item.url);
    if (uri == null) return;
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: TextField(
          controller: _controller,
          autofocus: true,
          onChanged: _onChanged,
          decoration: const InputDecoration(
            hintText: 'Search your saves',
            border: InputBorder.none,
          ),
        ),
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_error != null) {
      return _centred("Search failed.\n$_error");
    }
    if (_query.isEmpty) {
      return _centred('Type to search your saves');
    }
    // Keep showing the previous results while a new query is in flight, so the
    // screen doesn't flash empty on every keystroke (TASKS.md 3.1).
    if (_loading && _results.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    if (_results.isEmpty) {
      return _centred("No matches for '$_query'");
    }

    return ListView.separated(
      itemCount: _results.length,
      separatorBuilder: (context, index) => const Divider(height: 1),
      itemBuilder: (context, index) {
        final item = _results[index];
        return ItemCard(item: item, onTap: () => _openItem(item));
      },
    );
  }

  Widget _centred(String text) => Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(text, textAlign: TextAlign.center),
        ),
      );
}
