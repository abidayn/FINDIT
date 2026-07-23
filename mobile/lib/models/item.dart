/// Mirrors `Item` in backend/models/schemas.py — one row of the `items` table
/// and the response body of POST /save. Keep the two in sync when either changes.
///
/// Two backend fields are deliberately not mirrored: `raw_content` (the full
/// fetched article text — potentially huge, and no screen displays it) and
/// `user_id` (always null until auth exists). Extra JSON keys are simply
/// ignored by `fromJson`, so leaving them out costs nothing.
class Item {
  final String id;
  final String url;
  final String title;
  final String? summary;
  final String folder;
  final String? source;
  final String? thumbnailUrl;
  final DateTime createdAt;
  final String? confidence;

  /// "ok" when the AI ran cleanly, "failed" when the backend saved with
  /// fallback values. Lets the UI tell the user the save worked but the
  /// title/summary are placeholders.
  final String? aiStatus;

  const Item({
    required this.id,
    required this.url,
    required this.title,
    required this.folder,
    required this.createdAt,
    this.summary,
    this.source,
    this.thumbnailUrl,
    this.confidence,
    this.aiStatus,
  });

  factory Item.fromJson(Map<String, dynamic> json) {
    return Item(
      id: json['id'] as String,
      url: json['url'] as String,
      title: json['title'] as String,
      summary: json['summary'] as String?,
      folder: json['folder'] as String,
      source: json['source'] as String?,
      thumbnailUrl: json['thumbnail_url'] as String?,
      createdAt: DateTime.parse(json['created_at'] as String),
      confidence: json['confidence'] as String?,
      aiStatus: json['ai_status'] as String?,
    );
  }
}
