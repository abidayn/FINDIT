import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../constants.dart';
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

            // Split off items still waiting on the AI (daily quota hit). Keeping
            // them out of `organized` means the folder chips and their counts
            // describe only real, classified items — a pending item's
            // placeholder "Other" would otherwise inflate the Other count and
            // show junk titles inside it.
            final pending = allItems.where((i) => i.isPending).toList();
            final organized = allItems.where((i) => !i.isPending).toList();

            final visible = _selectedFolder == null
                ? organized
                : organized.where((i) => i.folder == _selectedFolder).toList();

            // Processing only surfaces in the "All" view: it's a home-level
            // status, not something to repeat at the top of every folder.
            final showProcessing = _selectedFolder == null && pending.isNotEmpty;

            return Column(
              children: [
                _FolderChips(
                  allItems: organized,
                  selected: _selectedFolder,
                  onSelect: (folder) =>
                      setState(() => _selectedFolder = folder),
                ),
                const Divider(height: 1),
                Expanded(
                  // CustomScrollView so a fixed "Processing" header can sit
                  // above a lazily-built list in one scroll view. Slivers are
                  // just scrollable sections; SliverList stays lazy like
                  // ListView.builder, so a long library still isn't all built
                  // at once.
                  child: CustomScrollView(
                    // Keep it scrollable even when short, so pull-to-refresh
                    // works on a nearly-empty screen.
                    physics: const AlwaysScrollableScrollPhysics(),
                    slivers: [
                      if (showProcessing)
                        SliverToBoxAdapter(
                          child: _ProcessingSection(
                            items: pending,
                            onOpen: _openItem,
                          ),
                        ),
                      if (visible.isNotEmpty)
                        SliverList.separated(
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
                        )
                      // Only show a "nothing here" message when there's truly
                      // nothing — not when the processing section is carrying
                      // the screen on its own.
                      else if (!showProcessing)
                        SliverFillRemaining(
                          hasScrollBody: false,
                          child: _Message(
                            text: 'Nothing in ${_selectedFolder?.label} yet.',
                          ),
                        ),
                    ],
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

/// The "Processing" group at the top of the home list: items that saved fine
/// but haven't been organised yet because the daily AI limit was reached. The
/// backend reprocesses them automatically, so this is a temporary holding area,
/// not a folder — it disappears on its own once the limit resets and the items
/// get their real titles and folders.
class _ProcessingSection extends StatelessWidget {
  final List<Item> items;
  final ValueChanged<Item> onOpen;

  const _ProcessingSection({required this.items, required this.onOpen});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
          child: Row(
            children: [
              Icon(Icons.hourglass_empty, size: 18, color: scheme.onSurfaceVariant),
              const SizedBox(width: 8),
              Text(
                'Processing (${items.length})',
                style: const TextStyle(fontWeight: FontWeight.w600),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
          child: Text(
            'Saved, waiting for the daily AI limit to reset. These sort '
            'themselves automatically.',
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ),
        for (final item in items)
          _PendingCard(item: item, onTap: () => onOpen(item)),
        // A heavier divider marks where the temporary section ends and the real
        // library begins.
        const Divider(height: 1, thickness: 6),
      ],
    );
  }
}

/// A single pending item. Deliberately not an [ItemCard]: its title and summary
/// are placeholders ("Untitled saved item"), so showing them as if they were
/// real would look like the save failed. Instead this shows the link itself,
/// which is the one thing we do know, and the user can still open it.
class _PendingCard extends StatelessWidget {
  final Item item;
  final VoidCallback onTap;

  const _PendingCard({required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    // The host is a readable stand-in for the missing title, e.g. a bare
    // "tiktok.com" instead of "Untitled saved item".
    final host = Uri.tryParse(item.url)?.host ?? item.url;

    return ListTile(
      onTap: onTap,
      leading: Container(
        width: 40,
        height: 40,
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
        ),
        child: Icon(iconForSource(item.source), color: scheme.onSurfaceVariant),
      ),
      title: Text(host, maxLines: 1, overflow: TextOverflow.ellipsis),
      subtitle: const Text('Waiting for AI…'),
      trailing: Icon(Icons.hourglass_empty, size: 16, color: scheme.onSurfaceVariant),
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
