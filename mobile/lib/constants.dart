import 'package:flutter/material.dart';

import 'models/folder.dart';

/// One colour per folder, so a badge is recognisable at a glance before you
/// read it. Each pair is a light background with a much darker foreground —
/// that contrast is what keeps the small badge text legible.
///
/// Phase 3 task 3.5 revisits these for a deliberate palette; for now they only
/// need to be distinct and readable.
const Map<Folder, Color> folderColors = {
  Folder.selfGrowth: Color(0xFFC8E6C9),
  Folder.productivity: Color(0xFFBBDEFB),
  Folder.techAndCoding: Color(0xFFD1C4E9),
  Folder.finance: Color(0xFFB2DFDB),
  Folder.cookingAndFood: Color(0xFFFFE0B2),
  Folder.fitnessAndHealth: Color(0xFFFFCDD2),
  Folder.entertainment: Color(0xFFF8BBD0),
  Folder.learning: Color(0xFFFFF9C4),
  Folder.other: Color(0xFFE0E0E0),
};

const Map<Folder, Color> folderTextColors = {
  Folder.selfGrowth: Color(0xFF1B5E20),
  Folder.productivity: Color(0xFF0D47A1),
  Folder.techAndCoding: Color(0xFF311B92),
  Folder.finance: Color(0xFF004D40),
  Folder.cookingAndFood: Color(0xFFE65100),
  Folder.fitnessAndHealth: Color(0xFFB71C1C),
  Folder.entertainment: Color(0xFF880E4F),
  Folder.learning: Color(0xFFF57F17),
  Folder.other: Color(0xFF424242),
};

/// Icon per source platform, used when an item has no thumbnail. The strings
/// match `Platform` in backend/models/schemas.py.
IconData iconForSource(String? source) {
  switch (source) {
    case 'youtube':
      return Icons.play_circle_outline;
    case 'tiktok':
      return Icons.music_note;
    case 'instagram':
      return Icons.photo_camera_outlined;
    case 'twitter':
      return Icons.chat_bubble_outline;
    case 'article':
      return Icons.article_outlined;
    default:
      return Icons.link;
  }
}
