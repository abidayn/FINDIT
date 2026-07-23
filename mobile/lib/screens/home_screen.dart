import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../models/folder.dart';
import '../models/item.dart';
import '../services/api_client.dart';
import '../widgets/item_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  late Future<List<Item>> _itemsFuture;

  /// null means "All". Filtering happens on the already-fetched list rather
  /// than re-hitting `/items?folder=`: the whole library is already in memory,
  /// so a round trip per chip tap would be slower and pointlessly chatty.
  Folder? _selectedFolder;

  @override
  void initState() {
    super.initState();
    _itemsFuture = getAllItems();
  }

  // Assigning a new Future is what makes FutureBuilder re-run; setState alone
  // would rebuild with the same already-resolved Future.
  Future<void> _refresh() async {
    final future = getAllItems();
    setState(() {
      _itemsFuture = future;
    });
    // RefreshIndicator keeps its spinner up until this completes, so await the
    // same Future the list is waiting on rather than returning immediately.
    await future;
  }

  Future<void> _openItem(Item item) async {
    final uri = Uri.tryParse(item.url);
    if (uri == null) return;

    // externalApplication so a TikTok link opens the TikTok app rather than a
    // browser tab inside Fetch.
    final launched = await launchUrl(uri, mode: LaunchMode.externalApplication);

    if (!launched && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Couldn't open ${item.url}")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Fetch'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            // Refresh on return: a search result may have been opened and the
            // library may have changed while this screen sat in the background.
            onPressed: () => context.push('/search').then((_) => _refresh()),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _refresh,
        child: FutureBuilder<List<Item>>(
          future: _itemsFuture,
          builder: (context, snapshot) {
            if (snapshot.connectionState == ConnectionState.waiting) {
              return const Center(child: CircularProgressIndicator());
            }
            if (snapshot.hasError) {
              return _Message(
                text: "Couldn't load your saves.\n${snapshot.error}",
              );
            }

            final allItems = snapshot.data ?? [];
            if (allItems.isEmpty) {
              return const _Message(
                text: 'Nothing saved yet.\nShare a link to get started.',
              );
            }

            final visible = _selectedFolder == null
                ? allItems
                : allItems.where((i) => i.folder == _selectedFolder).toList();

            return Column(
              children: [
                _FolderChips(
                  allItems: allItems,
                  selected: _selectedFolder,
                  onSelect: (folder) =>
                      setState(() => _selectedFolder = folder),
                ),
                const Divider(height: 1),
                Expanded(
                  child: visible.isEmpty
                      ? _Message(
                          text: 'Nothing in ${_selectedFolder?.label} yet.',
                        )
                      : ListView.separated(
                          itemCount: visible.length,
                          separatorBuilder: (context, index) =>
                              const Divider(height: 1),
                          itemBuilder: (context, index) {
                            final item = visible[index];
                            return ItemCard(
                              item: item,
                              onTap: () => _openItem(item),
                            );
                          },
                        ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}

/// Horizontal row of folder chips: "All" plus every folder that actually has
/// items, each with its count. Folders with nothing in them are hidden — an
/// empty chip is a dead end the user can only be disappointed by.
class _FolderChips extends StatelessWidget {
  final List<Item> allItems;
  final Folder? selected;
  final ValueChanged<Folder?> onSelect;

  const _FolderChips({
    required this.allItems,
    required this.selected,
    required this.onSelect,
  });

  @override
  Widget build(BuildContext context) {
    final counts = <Folder, int>{};
    for (final item in allItems) {
      counts[item.folder] = (counts[item.folder] ?? 0) + 1;
    }

    // Iterate over Folder.values, not counts.keys, so chip order is the fixed
    // taxonomy order rather than whatever order items happened to arrive in.
    final present = Folder.values.where(counts.containsKey);

    return SizedBox(
      height: 52,
      child: ListView(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        children: [
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
            child: ChoiceChip(
              label: Text('All (${allItems.length})'),
              selected: selected == null,
              onSelected: (_) => onSelect(null),
            ),
          ),
          for (final folder in present)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
              child: ChoiceChip(
                label: Text('${folder.label} (${counts[folder]})'),
                selected: selected == folder,
                onSelected: (_) => onSelect(folder),
              ),
            ),
        ],
      ),
    );
  }
}

/// Centred text for the empty and error states. Wrapped in a scrollable so
/// pull-to-refresh still works when the list has no items to scroll.
class _Message extends StatelessWidget {
  final String text;

  const _Message({required this.text});

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        return SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          child: ConstrainedBox(
            constraints: BoxConstraints(minHeight: constraints.maxHeight),
            child: Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(text, textAlign: TextAlign.center),
              ),
            ),
          ),
        );
      },
    );
  }
}
