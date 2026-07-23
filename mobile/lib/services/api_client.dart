import 'dart:convert';

import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:http/http.dart' as http;

/// Calls the backend's `/health` endpoint and returns its `status` string
/// (e.g. "ok"). Throws on a missing config value, network failure, a
/// non-200 response, or an unexpected response shape — callers (typically
/// a FutureBuilder) are expected to catch/display the error, not this file.
Future<String> fetchHealth() async {
  final baseUrl = dotenv.env['API_URL'];
  if (baseUrl == null || baseUrl.isEmpty) {
    throw StateError('API_URL is not set — check mobile/.env');
  }

  // Railway's free tier can idle-sleep; give a cold start room before failing.
  final response = await http
      .get(Uri.parse('$baseUrl/health'))
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
