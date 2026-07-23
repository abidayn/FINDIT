import 'package:flutter/material.dart';

import '../constants.dart';
import '../models/item.dart';
import 'folder_badge.dart';

/// One saved item in the home list: thumbnail (or a platform icon when there
/// isn't one) on the left, text on the right, folder badge underneath.
class ItemCard extends StatelessWidget {
  final Item item;
  final VoidCallback onTap;

  const ItemCard({super.key, required this.item, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _Thumbnail(item: item),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    item.title,
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  // An item with no summary just skips the line rather than
                  // leaving an empty gap (TASKS.md 3.4).
                  if (item.summary != null && item.summary!.isNotEmpty) ...[
                    const SizedBox(height: 4),
                    Text(
                      item.summary!,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                  const SizedBox(height: 8),
                  FolderBadge(folder: item.folder),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Thumbnail extends StatelessWidget {
  final Item item;

  const _Thumbnail({required this.item});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final placeholder = Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        color: scheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Icon(iconForSource(item.source), color: scheme.onSurfaceVariant),
    );

    final url = item.thumbnailUrl;
    if (url == null || url.isEmpty) return placeholder;

    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: Image.network(
        url,
        width: 56,
        height: 56,
        fit: BoxFit.cover,
        // A dead thumbnail URL must not blow up the whole list — fall back to
        // the same icon we'd use if there were no thumbnail at all.
        errorBuilder: (context, error, stackTrace) => placeholder,
      ),
    );
  }
}
