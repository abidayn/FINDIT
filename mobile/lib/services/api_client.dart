import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

import '../models/item.dart';

/// Reads the backend base URL from the bundled .env, failing loudly if it's
/// missing rather than firing a request at a nonsense address.
String _baseUrl() {
  final url = dotenv.env['API_URL'];
  if (url == null || url.isEmpty) {
    throw StateError('API_URL is not set — check mobile/.env');
  }
  return url;
}

/// Calls the backend's `/health` endpoint and returns its `status` string
/// (e.g. "ok"). Throws on a missing config value, network failure, a
/// non-200 response, or an unexpected response shape — callers (typically
/// a FutureBuilder) are expected to catch/display the error, not this file.
Future<String> fetchHealth() async {
  // Railway's free tier can idle-sleep; give a cold start room before failing.
  final response = await http
      .get(Uri.parse('${_baseUrl()}/health'))
      .timeout(const Duration(seconds: 15));

  if (response.statusCode != 200) {
    throw Exception('Health check failed: HTTP ${response.statusCode}');
  }

  final body = jsonDecode(response.body) as Map<String, dynamic>;
  final status = body['status'];
  if (status is! String) {
    throw const FormatException('Unexpected /health response shape');
  }
  return status;
}

/// Sends [url] to the backend's POST /save, which fetches the content, runs it
/// through the AI, and stores the row — returning the saved [Item].
///
/// Throws on failure so the UI can show an error and offer a retry. Note the
/// backend never fails just because the fetch or the AI failed (it falls back
/// to placeholder values), so an error here means a real problem: no network,
/// a rejected URL (422), or the database write failing (500).
Future<Item> saveItem(String url) async {
  // 45s: the backend chains a content fetch (up to 10s) plus a Gemini call
  // that may retry once, on top of a possible Railway cold start.
  final response = await http
      .post(
        Uri.parse('${_baseUrl()}/save'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'url': url}),
      )
      .timeout(const Duration(seconds: 45));

  if (response.statusCode != 200) {
    throw Exception('Save failed: HTTP ${response.statusCode}');
  }

  return Item.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
}
