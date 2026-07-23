import 'package:flutter/material.dart';

import '../constants.dart';
import '../models/folder.dart';

/// A small coloured pill naming the folder an item was filed under.
class FolderBadge extends StatelessWidget {
  final Folder folder;

  const FolderBadge({super.key, required this.folder});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: folderColors[folder],
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        folder.label,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w500,
          color: folderTextColors[folder],
        ),
      ),
    );
  }
}
