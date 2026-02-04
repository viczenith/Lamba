import 'dart:convert';
import 'dart:async';
import 'package:file_picker/file_picker.dart';
import 'package:http/http.dart' as http;
import 'package:open_file/open_file.dart';
import 'package:path_provider/path_provider.dart';
import 'package:real_estate_app/admin/models/add_estate_plot_model.dart';
import 'package:real_estate_app/admin/models/admin_dashboard_data.dart';
import 'package:real_estate_app/shared/models/support_chat_model.dart';
import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:mime/mime.dart';
import 'package:http_parser/http_parser.dart';
import 'dart:io';
import 'package:path/path.dart' as p;
import 'package:real_estate_app/admin/models/add_plot_size.dart';
// ignore: unused_import
import 'package:real_estate_app/admin/models/add_amenities_model.dart';
import 'package:real_estate_app/admin/models/estate_details_model.dart';
// ignore: unused_import
import 'package:real_estate_app/admin/models/admin_user_registration.dart';
import 'package:real_estate_app/admin/models/plot_allocation_model.dart';
import 'package:real_estate_app/admin/models/plot_size_number_model.dart';
import 'package:intl/intl.dart';
import 'package:real_estate_app/core/config.dart';

class ApiService {
  // Use Config for dynamic backend selection (Render or localhost)
  late String baseUrl;

  ApiService() {
    baseUrl = Config.baseUrl;
    // Debug: surface which backend the running app is using.
    debugPrint(
        '⚙️ Config.useProductionBackend = ${Config.useProductionBackend}');
    debugPrint('⚙️ ApiService baseUrl = $baseUrl');
  }

  /// Login using username and password.
  Future<String> login(String email, String password) async {
    // Force-local testing: use the explicit dev base URL so requests hit localhost.
    final url = '${Config.devBaseUrl}/api-token-auth/';
    debugPrint('🔐 Login URL (dev forced): $url');
    debugPrint('⚙️ Runtime Config.devBaseUrl = ${Config.devBaseUrl}');
    debugPrint('📧 Email: $email');

    try {
      debugPrint('➡️ POST $url - payload: {"email":"•••", "password":"•••"}');
      final response = await http
          .post(
            Uri.parse(url),
            headers: {
              'Content-Type': 'application/json',
              'User-Agent': 'RealEstateMSApp/1.0 (Android)'
            },
            body: jsonEncode({'email': email, 'password': password}),
          )
          .timeout(
            const Duration(seconds: 30),
            onTimeout: () => throw TimeoutException(
                'Login request timed out after 30 seconds. Render backend may be slow to respond.'),
          );

      debugPrint('✅ Response Status: ${response.statusCode}');
      debugPrint('📦 Response Body: ${response.body}');

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        // Support backend that wraps payload in a {"success":..., "data": {...}} envelope
        String? token;
        if (data is Map<String, dynamic>) {
          if (data.containsKey('data') &&
              data['data'] is Map<String, dynamic>) {
            final payload = data['data'] as Map<String, dynamic>;
            token = payload['token']?.toString();
          } else {
            token = data['token']?.toString();
          }
        }
        debugPrint('🎉 Login successful! Token: $token');
        return token ?? '';
      } else {
        debugPrint('❌ Login failed with status ${response.statusCode}');
        throw Exception(
            'Login failed with status ${response.statusCode}: ${response.body}');
      }
    } on SocketException catch (e, st) {
      debugPrint('🔌 SocketException when connecting to $url: $e');
      debugPrint(st.toString());
      throw Exception('Network error: ${e.message}');
    } on TimeoutException catch (e) {
      debugPrint('⏱️ Timeout: $e');
      throw Exception('Login request timed out. Please check your connection.');
    } catch (e, st) {
      debugPrint('🔴 Login error: $e');
      debugPrint(st.toString());
      rethrow;
    }
  }

  /// Unified login to support multi-role selection.
  Future<Map<String, dynamic>> loginUnified(
    String email,
    String password, {
    int? selectedUserId,
    String? loginSlug,
  }) async {
    // Force-local testing: use the explicit dev base URL so requests hit localhost.
    final url = '${Config.devBaseUrl}/api-token-auth/';
    debugPrint('➡️ POST (unified) URL (dev forced): $url');
    debugPrint('⚙️ Runtime Config.devBaseUrl = ${Config.devBaseUrl}');

    final body = <String, dynamic>{
      // Include both `email` and `username` for compatibility with different
      // backends / form field names.
      'email': email,
      'username': email,
      'password': password,
    };
    if (selectedUserId != null) body['selected_user_id'] = selectedUserId;
    if (loginSlug != null && loginSlug.trim().isNotEmpty) {
      body['login_slug'] = loginSlug.trim();
    }

    try {
      debugPrint(
          '➡️ POST (unified) $url - payload keys: ${body.keys.toList()}');
      final response = await http
          .post(
            Uri.parse(url),
            headers: {
              'Content-Type': 'application/json',
              'X-Requested-With': 'XMLHttpRequest',
              'Accept': 'application/json',
              'User-Agent': 'RealEstateMSApp/1.0 (Android)'
            },
            body: jsonEncode(body),
          )
          .timeout(
            const Duration(seconds: 60),
            onTimeout: () => throw TimeoutException(
                'Login request timed out after 60 seconds. Server may be slow to respond.'),
          );

      debugPrint('✅ Response Status: ${response.statusCode}');
      debugPrint('📦 Response Body: ${response.body}');

      if (response.statusCode == 200 || response.statusCode == 409) {
        final decoded = jsonDecode(response.body);
        if (decoded is Map<String, dynamic>) {
          // Support backend that wraps payload in a {"success":..., "data": {...}} envelope
          if (decoded.containsKey('data') &&
              decoded['data'] is Map<String, dynamic>) {
            return decoded['data'] as Map<String, dynamic>;
          }

          // Fallback: token/user at the top level
          return decoded;
        }
        throw Exception('Unexpected login response: ${response.body}');
      }

      throw Exception(
          'Login failed with status ${response.statusCode}: ${response.body}');
    } on SocketException catch (e, st) {
      debugPrint('🔌 SocketException (unified) when connecting to $url: $e');
      debugPrint(st.toString());
      throw Exception('Network error: ${e.message}');
    } on TimeoutException catch (e) {
      debugPrint('⏱️ Timeout (unified): $e');
      throw Exception('Login request timed out. Please check your connection.');
    } catch (e, st) {
      debugPrint('🔴 LoginUnified error: $e');
      debugPrint(st.toString());
      rethrow;
    }
  }

  Future<Map<String, dynamic>> fetchSupportBirthdaySummary(String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/birthdays/summary/');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception(
          'Failed to load birthday summary: ${response.statusCode}');
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<Map<String, dynamic>> fetchSupportSpecialDayCounts(
      String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/special-days/counts/');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception(
          'Failed to load special day counts: ${response.statusCode}');
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw Exception('Unexpected response for special day counts');
  }

  Future<Map<String, dynamic>> fetchSupportBirthdayCounts(String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/birthdays/counts/');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to load birthday counts: ${response.statusCode}');
    }

    final decoded = jsonDecode(response.body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    throw Exception('Unexpected response for birthday counts');
  }

  Future<Map<String, dynamic>> fetchSupportSpecialDaySummary(
      String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/special-days/summary/');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to load special days: ${response.statusCode}');
    }

    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  Future<List<Map<String, dynamic>>> fetchCustomSpecialDays(
      String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/custom-special-days/');

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        final raw = decoded['customDays'];
        if (raw is List) {
          return raw
              .map<Map<String, dynamic>>((item) => item is Map
                  ? Map<String, dynamic>.from(item)
                  : <String, dynamic>{})
              .where((item) => item.isNotEmpty)
              .toList();
        }
      }
      return const [];
    }

    throw Exception(_extractErrorMessage(response) ??
        'Failed to load custom special days: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> createCustomSpecialDay({
    required String token,
    required String name,
    required DateTime date,
    String countryCode = 'NG',
    bool isRecurring = false,
    String category = 'custom',
    String? description,
  }) async {
    final uri = Uri.parse('$baseUrl/admin-support/custom-special-days/');
    final payload = <String, dynamic>{
      'name': name,
      'date': DateFormat('yyyy-MM-dd').format(date),
      'countryCode': countryCode,
      'isRecurring': isRecurring,
      'category': category,
    };
    if (description != null && description.trim().isNotEmpty) {
      payload['description'] = description.trim();
    }

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(payload),
    );

    if (response.statusCode == 201) {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic> &&
          decoded['customDay'] is Map<String, dynamic>) {
        return decoded['customDay'] as Map<String, dynamic>;
      }
      return const {};
    }

    throw Exception(_extractErrorMessage(response) ??
        'Failed to create custom special day: ${response.statusCode}');
  }

  Future<void> deleteCustomSpecialDay({
    required String token,
    required String dayId,
  }) async {
    final uri = Uri.parse('$baseUrl/admin-support/custom-special-days/$dayId/');

    final response = await http.delete(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 204) {
      return;
    }

    throw Exception(_extractErrorMessage(response) ??
        'Failed to delete custom special day: ${response.statusCode}');
  }

  String? _extractErrorMessage(http.Response response) {
    try {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) {
        for (final key in ['detail', 'error', 'message']) {
          final value = decoded[key];
          if (value == null) continue;
          if (value is String && value.trim().isNotEmpty) {
            return value.trim();
          }
          if (value is List && value.isNotEmpty) {
            return value.first.toString();
          }
        }
      }
      if (decoded is String && decoded.trim().isNotEmpty) {
        return decoded.trim();
      }
    } catch (_) {
      // ignore parse errors
    }
    return null;
  }

  // -------------------------------
  // Public registration endpoints
  // These endpoints expect form-encoded POSTs and return JSON when
  // the request contains the X-Requested-With: XMLHttpRequest header.
  // -------------------------------
  Future<Map<String, dynamic>> registerClient(
      Map<String, String> payload) async {
    final uri = Uri.parse('$baseUrl/client/register/');

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
      },
      body: payload,
    );

    try {
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 || response.statusCode == 201)
        return decoded;
      throw Exception(_extractErrorMessage(response) ??
          decoded['message'] ??
          'Client registration failed: ${response.statusCode}');
    } catch (_) {
      throw Exception('Client registration failed: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> registerMarketer(
      Map<String, String> payload) async {
    final uri = Uri.parse('$baseUrl/marketer/register/');

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
      },
      body: payload,
    );

    try {
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 || response.statusCode == 201)
        return decoded;
      throw Exception(_extractErrorMessage(response) ??
          decoded['message'] ??
          'Marketer registration failed: ${response.statusCode}');
    } catch (_) {
      throw Exception('Marketer registration failed: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> registerCompany(
      Map<String, String> payload) async {
    final uri = Uri.parse('$baseUrl/register/');

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json',
      },
      body: payload,
    );

    try {
      final decoded = jsonDecode(response.body) as Map<String, dynamic>;
      if (response.statusCode == 200 || response.statusCode == 201)
        return decoded;
      throw Exception(_extractErrorMessage(response) ??
          decoded['message'] ??
          'Company registration failed: ${response.statusCode}');
    } catch (_) {
      throw Exception('Company registration failed: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> deleteMarketerChatMessage({
    required String token,
    required int messageId,
  }) async {
    final uri = Uri.parse('$baseUrl/marketers/chat/$messageId/delete/');

    final response = await http.delete(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> payload =
          jsonDecode(response.body) as Map<String, dynamic>;
      final Map<String, dynamic> data =
          (payload['success'] == true && payload['data'] is Map)
              ? Map<String, dynamic>.from(payload['data'] as Map)
              : payload;

      final message = data['message'];
      if (message is Map<String, dynamic>) {
        final fileUrl = message['file_url']?.toString();
        if (fileUrl != null &&
            fileUrl.isNotEmpty &&
            !fileUrl.startsWith('http')) {
          message['file_url'] = _absUrl(fileUrl);
        }
      }

      return data;
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    if (response.statusCode == 403) {
      final Map<String, dynamic> error =
          jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(error['error'] ?? 'You cannot delete this message.');
    }

    if (response.statusCode == 404) {
      throw Exception('Message not found.');
    }

    throw Exception(
        'Failed to delete marketer message: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> deleteMarketerChatMessageForEveryone({
    required String token,
    required int messageId,
  }) async {
    final uri = Uri.parse('$baseUrl/marketers/chat/delete-for-everyone/');

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: jsonEncode({'message_id': messageId}),
    );

    final Map<String, dynamic> payload =
        jsonDecode(response.body) as Map<String, dynamic>;

    final Map<String, dynamic> data =
        (payload['success'] == true && payload['data'] is Map)
            ? Map<String, dynamic>.from(payload['data'] as Map)
            : payload;

    if (response.statusCode == 200 && payload['success'] == true) {
      final message = data['message'];
      if (message is Map<String, dynamic>) {
        final fileUrl = message['file_url']?.toString();
        if (fileUrl != null &&
            fileUrl.isNotEmpty &&
            !fileUrl.startsWith('http')) {
          message['file_url'] = _absUrl(fileUrl);
        }
      }
      return data;
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    if (response.statusCode == 403) {
      throw Exception(payload['error'] ??
          'You can only delete messages within 24 hours of sending.');
    }

    if (response.statusCode == 404) {
      throw Exception(payload['error'] ?? 'Message not found.');
    }

    throw Exception(payload['error'] ??
        'Failed to delete marketer message for everyone: ${response.statusCode}');
  }

  // ============================================================================
  // ADMIN SUPPORT CHAT API METHODS
  // ============================================================================

  Uri _supportChatUri(String role, String participantId, [String suffix = '']) {
    final normalizedRole = role.toLowerCase();
    final normalizedSuffix = suffix.startsWith('/') ? suffix : '/$suffix';
    return Uri.parse(
      '$baseUrl/admin-support/chat/$normalizedRole/$participantId$normalizedSuffix',
    );
  }

  void _normalizeSupportMessages(dynamic messages) {
    if (messages is! List) return;

    for (final entry in messages) {
      if (entry is Map<String, dynamic>) {
        final fileUrl = entry['file_url']?.toString();
        if (fileUrl != null &&
            fileUrl.isNotEmpty &&
            !fileUrl.startsWith('http')) {
          entry['file_url'] = _absUrl(fileUrl);
        }
        final avatar = entry['sender_avatar']?.toString();
        if (avatar != null && avatar.isNotEmpty && !avatar.startsWith('http')) {
          entry['sender_avatar'] = _absUrl(avatar);
        }
        if (entry['sender_avatar'] == null &&
            (entry['sender_role']?.toString().toLowerCase() == 'admin' ||
                entry['sender_role']?.toString().toLowerCase() == 'support')) {
          entry['sender_avatar'] = 'asset://assets/logo.png';
        }
      }
    }
  }

  Future<Map<String, dynamic>> fetchSupportChatThread({
    required String token,
    required String role,
    required String participantId,
    int? lastMessageId,
  }) async {
    final uri =
        _supportChatUri(role, participantId, '').replace(queryParameters: {
      if (lastMessageId != null) 'last_msg_id': '$lastMessageId',
    });

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> payload =
          jsonDecode(response.body) as Map<String, dynamic>;
      _normalizeSupportMessages(payload['messages']);
      return payload;
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    throw Exception(
        'Failed to load support conversation: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> sendSupportChatMessage({
    required String token,
    required String role,
    required String participantId,
    String? content,
    File? file,
    String messageType = 'enquiry',
    int? replyToId,
  }) async {
    final uri = _supportChatUri(role, participantId, '');

    final request = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Token $token'
      ..headers['Accept'] = 'application/json';

    if (content != null && content.trim().isNotEmpty) {
      request.fields['content'] = content.trim();
    }
    request.fields['message_type'] = messageType;
    if (replyToId != null) {
      request.fields['reply_to'] = replyToId.toString();
    }

    if (file != null) {
      final mime = lookupMimeType(file.path) ?? 'application/octet-stream';
      final parts = mime.split('/');
      request.files.add(await http.MultipartFile.fromPath(
        'file',
        file.path,
        contentType: MediaType(parts.first, parts.last),
      ));
    }

    if (request.fields['content'] == null && request.files.isEmpty) {
      throw Exception('Please provide either a message or attach a file.');
    }

    final streamed = await request.send();
    final response = await http.Response.fromStream(streamed);

    if (response.statusCode == 201) {
      final Map<String, dynamic> body =
          jsonDecode(response.body) as Map<String, dynamic>;
      _normalizeSupportMessages([body['message']]);
      return body;
    }

    if (response.statusCode == 400) {
      final Map<String, dynamic> error =
          jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(error['errors']?.toString() ?? 'Invalid message data.');
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    throw Exception('Failed to send support message: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> pollSupportChat({
    required String token,
    required String role,
    required String participantId,
    int lastMessageId = 0,
  }) async {
    final uri = _supportChatUri(role, participantId, '/poll/').replace(
      queryParameters: {'last_msg_id': '$lastMessageId'},
    );

    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> payload =
          jsonDecode(response.body) as Map<String, dynamic>;
      _normalizeSupportMessages(payload['new_messages']);
      return payload;
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    throw Exception('Failed to poll support chat: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> markSupportMessagesRead({
    required String token,
    required String role,
    required String participantId,
    List<int>? messageIds,
    bool markAll = false,
  }) async {
    final uri = _supportChatUri(role, participantId, '/mark-read/');
    final body = <String, dynamic>{};

    if (markAll) {
      body['mark_all'] = true;
    } else if (messageIds != null && messageIds.isNotEmpty) {
      body['message_ids'] = messageIds;
    } else {
      throw Exception('Provide messageIds or set markAll to true.');
    }

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: jsonEncode(body),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body) as Map<String, dynamic>;
    }

    if (response.statusCode == 400) {
      final Map<String, dynamic> error =
          jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(error['error']?.toString() ?? 'Invalid request.');
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    throw Exception(
        'Failed to mark support messages read: ${response.statusCode}');
  }

  Future<Map<String, dynamic>> deleteSupportMessage({
    required String token,
    required int messageId,
  }) async {
    final uri =
        Uri.parse('$baseUrl/admin-support/chat/messages/$messageId/delete/');

    final response = await http.delete(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> payload =
          jsonDecode(response.body) as Map<String, dynamic>;
      _normalizeSupportMessages([payload['message']]);
      return payload;
    }

    if (response.statusCode == 401) {
      throw Exception('Authentication failed. Please login again.');
    }

    if (response.statusCode == 403) {
      final Map<String, dynamic> error =
          jsonDecode(response.body) as Map<String, dynamic>;
      throw Exception(error['error'] ?? 'You cannot delete this message.');
    }

    if (response.statusCode == 404) {
      throw Exception('Message not found.');
    }

    throw Exception('Failed to delete support message: ${response.statusCode}');
  }

  Future<List<Chat>> fetchMarketerChats(String token) async {
    final uri = Uri.parse('$baseUrl/admin-support/marketer-chats/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final dynamic payload = jsonDecode(response.body);
        if (payload is List) {
          return payload
              .map((item) => Chat.fromJson(item as Map<String, dynamic>))
              .toList();
        }
        throw Exception('Unexpected marketer chat payload format.');
      }

      if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      }

      throw Exception('Failed to load marketer chats: ${response.statusCode}');
    } catch (e) {
      throw Exception('Error fetching marketer chats: $e');
    }
  }

  Future<List<Chat>> searchSupportParticipants({
    required String token,
    required bool isClient,
    required String query,
  }) async {
    final trimmed = query.trim();
    if (trimmed.isEmpty) return const <Chat>[];

    final segment = isClient ? 'clients' : 'marketers';
    final uri = Uri.parse('$baseUrl/admin-support/chat/search/$segment/')
        .replace(queryParameters: {'q': trimmed});

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> payload =
            jsonDecode(response.body) as Map<String, dynamic>;
        final key = isClient ? 'clients' : 'marketers';
        final results = payload[key];
        if (results is! List) return const <Chat>[];

        return results.map<Chat>((item) {
          final map = Map<String, dynamic>.from(item as Map<String, dynamic>);
          final avatar = map['profile_image']?.toString();
          if (avatar != null && avatar.isNotEmpty) {
            map['profile_image'] = _absUrl(avatar);
          }
          return Chat.directoryEntry(map);
        }).toList();
      }

      if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      }

      throw Exception(
          'Failed to search ${isClient ? 'clients' : 'marketers'}: ${response.statusCode}');
    } catch (e) {
      throw Exception(
          'Error searching ${isClient ? 'clients' : 'marketers'}: $e');
    }
  }

  Future<void> registerDeviceToken({
    required String authToken,
    required String fcmToken,
    required String platform,
    String? appVersion,
    String? deviceModel,
  }) async {
    final uri = Uri.parse('$baseUrl/device-tokens/register/');
    final payload = <String, dynamic>{
      'token': fcmToken,
      'platform': platform,
    };
    if (appVersion != null && appVersion.isNotEmpty) {
      payload['app_version'] = appVersion;
    }
    if (deviceModel != null && deviceModel.isNotEmpty) {
      payload['device_model'] = deviceModel;
    }

    final response = await http.post(
      uri,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $authToken',
      },
      body: jsonEncode(payload),
    );

    if (response.statusCode != 201) {
      throw Exception('Failed to register device token: ${response.body}');
    }
  }

  Future<void> deleteDeviceToken({
    required String authToken,
    required String fcmToken,
  }) async {
    final uri = Uri.parse('$baseUrl/device-tokens/register/').replace(
      queryParameters: {'token': fcmToken},
    );

    final response = await http.delete(
      uri,
      headers: {
        'Authorization': 'Token $authToken',
      },
    );

    if (response.statusCode != 204 && response.statusCode != 404) {
      throw Exception('Failed to delete device token: ${response.body}');
    }
  }

  // User Registration API Call
  Future<void> registerAdminUser(
      Map<String, dynamic> userData, String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/admin-user-registration/'),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
      body: jsonEncode(userData),
    );

    if (response.statusCode != 201) {
      throw Exception('Failed to register user: ${response.body}');
    }
  }

  // Fetch clients from the backend
  Future<List<Map<String, dynamic>>> fetchClients(String token) async {
    final url = Uri.parse('$baseUrl/clients/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    } else {
      throw Exception('Failed to load clients: ${response.statusCode}');
    }
  }

  // Get client detail
  Future<Map<String, dynamic>> getClientDetail({
    required int clientId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/client/$clientId/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      final data = (decoded is Map &&
              decoded.containsKey('data') &&
              decoded['success'] == true)
          ? decoded['data']
          : decoded;

      if (data is Map &&
          data['profile_image'] != null &&
          !data['profile_image'].toString().startsWith('http')) {
        data['profile_image'] = '$baseUrl${data['profile_image']}';
      }

      return data;
    } else {
      throw Exception('Failed to fetch client details');
    }
  }

  // Update client profile
  Future<void> updateClientProfile({
    required int clientId,
    required String token,
    String? fullName,
    String? about,
    String? company,
    String? job,
    String? country,
    String? address,
    String? phone,
    String? email,
    File? profileImage,
  }) async {
    final uri = Uri.parse('$baseUrl/client/$clientId/');
    final request = http.MultipartRequest('PUT', uri);

    // Auth token
    request.headers['Authorization'] = 'Token $token';
    request.headers['Accept'] = 'application/json';

    // Helper to add only non-null, non-empty fields
    void addField(String key, String? value) {
      if (value != null && value.isNotEmpty) {
        request.fields[key] = value;
      }
    }

    addField('full_name', fullName);
    addField('about', about);
    addField('company', company);
    addField('job', job);
    addField('country', country);
    addField('address', address);
    addField('phone', phone);
    addField('email', email);

    // Attach image file if present
    if (profileImage != null) {
      request.files.add(await http.MultipartFile.fromPath(
        'profile_image',
        profileImage.path,
      ));
    }

    // Send request
    final response = await request.send();

    // Handle response
    if (response.statusCode != 200) {
      final responseBody = await response.stream.bytesToString();
      throw Exception('Failed to update client: $responseBody');
    }
  }

  // Delete client
  Future<bool> deleteClient(String token, String clientId) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/client/$clientId/'),
      headers: {
        'Authorization': 'Token $token',
      },
    );

    if (response.statusCode == 204) {
      return true;
    } else {
      throw Exception('Failed to delete client');
    }
  }

  // Fetch marketers from the backend
  Future<List<Map<String, dynamic>>> fetchMarketers(String token) async {
    final url = Uri.parse('$baseUrl/marketers/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((e) => e as Map<String, dynamic>).toList();
    } else {
      throw Exception('Failed to load marketers: ${response.statusCode}');
    }
  }

  // Get marketer detail
  Future<Map<String, dynamic>> getMarketerDetail({
    required int marketerId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/marketers/$marketerId/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      final data = (decoded is Map &&
              decoded.containsKey('data') &&
              decoded['success'] == true)
          ? decoded['data']
          : decoded;

      // Check if the profile_image field is not null and handle dynamic URLs
      if (data is Map &&
          data['profile_image'] != null &&
          !data['profile_image'].toString().startsWith('http')) {
        data['profile_image'] = '$baseUrl${data['profile_image']}';
      }

      return data;
    } else {
      throw Exception('Failed to fetch marketer details');
    }
  }

  // Update marketer profile
  Future<void> updateMarketerProfile({
    required int marketerId,
    required String token,
    String? fullName,
    String? about,
    String? company,
    String? job,
    String? country,
    String? address,
    String? phone,
    String? email,
    File? profileImage,
  }) async {
    final uri = Uri.parse('$baseUrl/marketers/$marketerId/');
    final request = http.MultipartRequest('PUT', uri);

    // Auth token
    request.headers['Authorization'] = 'Token $token';
    request.headers['Accept'] = 'application/json';

    // Helper to add only non-null, non-empty fields
    void addField(String key, String? value) {
      if (value != null && value.isNotEmpty) {
        request.fields[key] = value;
      }
    }

    addField('full_name', fullName);
    addField('about', about);
    addField('company', company);
    addField('job', job);
    addField('country', country);
    addField('address', address);
    addField('phone', phone);
    addField('email', email);

    // Attach image file if present
    if (profileImage != null) {
      request.files.add(await http.MultipartFile.fromPath(
        'profile_image',
        profileImage.path,
      ));
    }

    // Send request
    final response = await request.send();

    // Handle response
    if (response.statusCode != 200) {
      final responseBody = await response.stream.bytesToString();
      throw Exception('Failed to update marketer: $responseBody');
    }
  }

  // Delete marketer
  Future<bool> deleteMarketer(String token, String id) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/marketers/$id/'),
      headers: {
        'Authorization': 'Token $token',
      },
    );

    if (response.statusCode == 204) {
      return true;
    } else {
      throw Exception('Failed to delete marketer');
    }
  }

  /// Get the current user's profile.
  Future<Map<String, dynamic>> getUserProfile(String token) async {
    final url = '$baseUrl/users/me/';
    final response = await http.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
    );

    final parsed = await _handleResponse(response);
    if (parsed is Map<String, dynamic>) {
      final Map<String, dynamic> data = (parsed.containsKey('data') &&
              parsed['success'] == true &&
              parsed['data'] is Map<String, dynamic>)
          ? Map<String, dynamic>.from(parsed['data'])
          : Map<String, dynamic>.from(parsed);

      return data;
    }

    throw ApiException(
      message: 'Unexpected user profile response',
      details: 'Expected JSON object but received ${parsed.runtimeType}',
      statusCode: response.statusCode,
    );
  }

  /// Fetch Admin Dashboard Data from the dynamic JSON endpoint.
  Future<AdminDashboardData> fetchAdminDashboard(String token) async {
    final url = '$baseUrl/admin/dashboard-data/';
    final response = await http.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
    );

    final parsed = await _handleResponse(response);
    if (parsed is Map<String, dynamic>) {
      return AdminDashboardData.fromJson(parsed);
    }

    throw ApiException(
      message: 'Unexpected dashboard response',
      details:
          'Expected JSON object for dashboard data but received ${parsed.runtimeType}',
      statusCode: response.statusCode,
    );
  }

  /// - Allocation details
  Future<Map<String, dynamic>> fetchEstateFullAllocationDetails(
      String estateId, String token) async {
    final url = '$baseUrl/estate-full-allocation-details/$estateId/';
    try {
      final response = await http.get(
        Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Token $token',
        },
      );

      switch (response.statusCode) {
        case 200:
          return json.decode(response.body);
        case 404:
          throw Exception('Estate not found');
        case 401:
          throw Exception('Authentication failed: Invalid or expired token');
        case 403:
          throw Exception('Permission denied: Check your access rights');
        case 500:
          throw Exception('Server error: Please try again later');
        default:
          throw Exception(
              'Failed to load estate details: ${response.statusCode} - ${response.body}');
      }
    } on http.ClientException catch (e) {
      throw Exception('Network error: ${e.message} (Check your connection)');
    } on FormatException catch (e) {
      throw Exception('Invalid response format: ${e.message}');
    } catch (e) {
      throw Exception('Unexpected error: $e');
    }
  }

  Future<void> updateAllocatedPlotForEstate(
    String allocationId,
    Map<String, dynamic> data,
    String token,
  ) async {
    final uri =
        Uri.parse('$baseUrl/update-allocated-plot-for-estate/$allocationId/');

    final resp = await http.patch(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(data),
    );

    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      final data = (decoded is Map &&
              decoded.containsKey('data') &&
              decoded['success'] == true)
          ? decoded['data']
          : decoded;

      return data;
    } else {}
  }

  Future<List<dynamic>> loadPlots(String token, int estateId) async {
    final url = '$baseUrl/load-plots/?estate_id=$estateId';
    final response = await http.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
    );
    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load plots: ${response.body}');
    }
  }

  /// Delete an allocation by its ID.
  Future<bool> deleteAllocation(String token, int allocationId) async {
    final url = '$baseUrl/delete-allocation/';
    final response = await http.post(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
      body: jsonEncode({'allocation_id': allocationId}),
    );
    if (response.statusCode == 200) {
      final data = jsonDecode(response.body);
      return data['success'] == true;
    } else {
      throw Exception('Failed to delete allocation: ${response.body}');
    }
  }

  Future<http.Response> downloadAllocations(String token, int estateId) async {
    final url = '$baseUrl/download-allocations/?estate_id=$estateId';
    return await http.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
    );
  }

  /// Download estate details as a PDF.
  Future<http.Response> downloadEstatePDF(String token, int estateId) async {
    final url = '$baseUrl/download-estate-pdf/$estateId/';
    return await http.get(
      Uri.parse(url),
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
    );
  }

  Future<Map<String, dynamic>> getEstatePlot({
    required String estateId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/estates/$estateId/plot/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception(
          'Failed to load estate plot. Status: ${response.statusCode}');
    }
  }

  Future<void> updateEstatePlot({
    required String estateId,
    required String token,
    required Map<String, dynamic> data,
  }) async {
    final url = Uri.parse('$baseUrl/estates/$estateId/plot/');
    final response = await http.post(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode(data),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update estate plot: ${response.body}');
    }
  }

  Future<void> updateAllocatedPlot(
      String id, Map<String, dynamic> data, String token) async {
    final url = Uri.parse('$baseUrl/update-allocated-plot/');
    final response = await http.post(
      url,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Token $token',
      },
      body: jsonEncode(data),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update allocation: ${response.body}');
    }
  }

  final Dio _dio = Dio();
  Future<void> uploadEstateLayout({
    required String estateId,
    required File layoutImage,
    required String token,
  }) async {
    try {
      final formData = FormData.fromMap({
        'estate': estateId,
        'layout_image': await MultipartFile.fromFile(layoutImage.path),
      });

      final response = await _dio.post(
        '$baseUrl/upload-estate-layout/',
        data: formData,
        options: Options(
          headers: {'Authorization': 'Token $token'},
        ),
      );

      if (response.statusCode != 201) {
        throw Exception('Failed to upload layout: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Upload error: $e');
    }
  }

  // get-plot-sizes
  Future<List<PlotSize>> getPlotSizesForEstate({
    required String estateId,
    required String token,
  }) async {
    try {
      final response = await _dio.get(
        '$baseUrl/get-plot-sizes/$estateId/',
        options: Options(headers: {'Authorization': 'Token $token'}),
      );
      if (response.statusCode == 200) {
        final data = response.data as List;
        // Convert each dynamic json map into a PlotSize instance
        return data
            .map((json) =>
                PlotSize(id: json['id'].toString(), size: json['size']))
            .toList();
      } else {
        throw Exception('Failed to load plot sizes');
      }
    } catch (e) {
      throw Exception('Error fetching plot sizes: $e');
    }
  }

  /// Upload prototype
  Future<void> uploadEstatePrototype({
    required String estateId,
    required String plotSizeId,
    required File prototypeImage,
    required String title,
    required String description,
    required String token,
  }) async {
    try {
      final formData = FormData.fromMap({
        'estate': estateId,
        'plot_size': plotSizeId,
        'prototype_image': await MultipartFile.fromFile(prototypeImage.path),
        'Title': title,
        'Description': description,
      });

      final response = await _dio.post(
        '$baseUrl/upload-prototype/',
        data: formData,
        options: Options(
          headers: {'Authorization': 'Token $token'},
          contentType: 'multipart/form-data',
        ),
      );

      if (response.statusCode != 201) {
        throw Exception('Failed to upload prototype: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Upload error: $e');
    }
  }

  /// Uploads a floor plan via the Django API.
  Future<void> uploadFloorPlan({
    required String estateId,
    required String plotSizeId,
    required File floorPlanImage,
    required String planTitle,
    String? description,
    required String token,
  }) async {
    final formData = FormData.fromMap({
      'estate': estateId,
      'plot_size': plotSizeId,
      'floor_plan_image': await MultipartFile.fromFile(floorPlanImage.path),
      'plan_title': planTitle,
      if (description != null && description.isNotEmpty)
        'description': description,
    });

    final response = await _dio.post(
      '$baseUrl/upload-floor-plan/',
      data: formData,
      options: Options(headers: {'Authorization': 'Token $token'}),
    );

    if (response.statusCode != 201) {
      throw Exception('Failed to upload floor plan: ${response.statusCode}');
    }
  }

  /// Update estate amenities via the Django API
  Future<void> updateEstateAmenities({
    required String estateId,
    required List<String> amenities,
    required String token,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/update-estate-amenities/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        'estate': estateId,
        'amenities': amenities,
      }),
    );
    if (response.statusCode != 200) {
      throw Exception('Failed to update amenities: ${response.statusCode}');
    }
  }

  /// Fetch available amenities from the API
  Future<List<dynamic>> getAvailableAmenities(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/get-available-amenities/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to load amenities: ${response.statusCode}');
    }
  }

  /// Updates the work progress for the estate
  Future<void> updateWorkProgress({
    required String estateId,
    required String progressStatus,
    required String token,
  }) async {
    final response = await _dio.post(
      '$baseUrl/update-work-progress/$estateId/',
      data: {'progress_status': progressStatus},
      options: Options(headers: {'Authorization': 'Token $token'}),
    );
    if (response.statusCode != 201) {
      throw Exception('Failed to update progress: ${response.statusCode}');
    }
  }

  /// Fetches the current estate map data using a GET request.
  Future<Map<String, dynamic>?> getEstateMap({
    required String estateId,
    required String token,
  }) async {
    try {
      final response = await _dio.get(
        '$baseUrl/update-estate-map/$estateId/',
        options: Options(headers: {'Authorization': 'Token $token'}),
      );
      if (response.statusCode == 200) {
        return response.data;
      } else if (response.statusCode == 404) {
        return null;
      } else {
        throw Exception('Failed to load map data: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Updates the estate map with new data using a POST request.
  Future<void> updateEstateMap({
    required String estateId,
    required String latitude,
    required String longitude,
    String? googleMapLink,
    required String token,
  }) async {
    final data = {
      'latitude': latitude,
      'longitude': longitude,
      if (googleMapLink != null) 'google_map_link': googleMapLink,
    };
    try {
      final response = await _dio.post(
        '$baseUrl/update-estate-map/$estateId/',
        data: data,
        options: Options(headers: {'Authorization': 'Token $token'}),
      );
      if (response.statusCode != 200) {
        throw Exception('Failed to update map: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  /// Estate Details
  Future<Estate> getEstateDetails(String estateId, String token) async {
    final url = Uri.parse('$baseUrl/estate-details/$estateId/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final jsonData = jsonDecode(response.body);
      return Estate.fromJson(jsonData);
    } else if (response.statusCode == 404) {
      throw Exception('Estate not found');
    } else {
      throw Exception('Failed to load estate details: ${response.statusCode}');
    }
  }

  ////// ADD ESTATE PLOTS

  /// Fetch the list of all estates.
  Future<List<Map<String, dynamic>>> fetchEstates(
      {required String token}) async {
    final url = Uri.parse('$baseUrl/estates/');
    final response = await http.get(url, headers: {
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
    });

    if (response.statusCode == 200) {
      final List data = json.decode(response.body);
      return List<Map<String, dynamic>>.from(data);
    } else {
      throw Exception("Could not fetch estates. Please try again.");
    }
  }

  // Update/Edit Estate
  Future<void> updateEstate({
    required String token,
    required String estateId,
    required Map<String, dynamic> data,
  }) async {
    final url = Uri.parse('$baseUrl/estates/$estateId/');
    final response = await http.put(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode(data),
    );

    if (response.statusCode != 200) {
      throw Exception(
          'Failed to update estate. Status code: ${response.statusCode}');
    }
  }

  /// Fetch details for Add Estate Plot for a given estate.
  Future<EstatePlotDetails> fetchAddEstatePlotDetails({
    required int estateId,
    required String token,
  }) async {
    final url = Uri.parse('$baseUrl/get-add-estate-plot-details/$estateId/');
    final response = await http.get(url, headers: {
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
    });

    if (response.statusCode == 200) {
      final Map<String, dynamic> data = json.decode(response.body);
      return EstatePlotDetails.fromJson(data);
    } else {
      throw Exception(
          "Could not retrieve plot details. Please try again later.");
    }
  }

  Future<dynamic> _handleResponse(http.Response response) async {
    try {
      // Explicitly decode with UTF-8 to handle emojis and special characters correctly
      final decodedBody = utf8.decode(response.bodyBytes);

      // If server returned HTML (e.g., an error page), surface a clear ApiException
      final contentType = response.headers['content-type']?.toLowerCase() ?? '';
      // Be more robust detecting HTML (allow for BOM/whitespace before the tag)
      final bodySnippet = decodedBody.length > 1024
          ? decodedBody.substring(0, 1024)
          : decodedBody;
      final looksLikeHtml = contentType.contains('text/html') ||
          RegExp(r'^[\uFEFF\s]*<(?:!doctype|html)', caseSensitive: false)
              .hasMatch(bodySnippet) ||
          bodySnippet.toLowerCase().contains('<!doctype');

      debugPrint('🔎 Response content-type: $contentType');
      if (looksLikeHtml) {
        final preview = bodySnippet.length > 512
            ? bodySnippet.substring(0, 512) + '...'
            : bodySnippet;
        debugPrint(
            '⚠️ Received non-JSON response (status ${response.statusCode}): $preview');
        throw ApiException(
          message: 'Received non-JSON (HTML) response from server',
          details:
              'Status: ${response.statusCode}. Response preview: ${preview.replaceAll('\n', ' ')}',
          statusCode: response.statusCode,
        );
      }

      // Attempt JSON decode
      final responseBody = json.decode(decodedBody);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        return responseBody;
      } else {
        final errorData =
            responseBody is Map ? responseBody : {'message': decodedBody};
        throw ApiException(
          message: errorData['message']?.toString() ?? 'An error occurred',
          details: errorData['details']?.toString() ??
              errorData['error']?.toString() ??
              'Please try again later',
          statusCode: response.statusCode,
        );
      }
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException(
        message: 'Failed to process response',
        details: e.toString(),
        statusCode: response.statusCode,
      );
    }
  }

  Future<Map<String, dynamic>> submitEstatePlot({
    required String token,
    required Map<String, dynamic> payload,
  }) async {
    try {
      final url = Uri.parse('$baseUrl/add-estate-plot/');
      final response = await http
          .post(
            url,
            headers: {
              'Content-Type': 'application/json',
              'Authorization': 'Token $token',
            },
            body: json.encode(payload),
          )
          .timeout(const Duration(seconds: 30));

      return await _handleResponse(response);
    } on http.ClientException catch (e) {
      throw ApiException(
        message: 'Network error',
        details: e.message,
        statusCode: 0,
      );
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException(
        message: 'Unexpected error',
        details: e.toString(),
        statusCode: 0,
      );
    }
  }

  // PLOT ALLOCATION
  Future<List<ClientForPlotAllocation>> fetchClientsForPlotAllocation(
      String token) async {
    final url = Uri.parse('$baseUrl/clients/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body) as List;
      return data
          .map((e) =>
              ClientForPlotAllocation.fromJson(e as Map<String, dynamic>))
          .toList();
    } else {
      throw Exception('Failed to load clients (${response.statusCode})');
    }
  }

  Future<List<EstateForPlotAllocation>> fetchEstatesForPlotAllocation(
      String token) async {
    final url = Uri.parse('$baseUrl/estates/');
    final response = await http.get(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body) as List;
      return data
          .map((e) =>
              EstateForPlotAllocation.fromJson(e as Map<String, dynamic>))
          .toList();
    } else {
      throw Exception('Failed to load estates (${response.statusCode})');
    }
  }

  Future<PlotAllocationResponse> loadPlotsForPlotAllocation(
      int estateId, String token) async {
    final url = Uri.parse(
        '$baseUrl/load-plots-for-plot-allocation/?estate_id=$estateId');

    try {
      final response = await http.get(
        url,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final responseData = jsonDecode(response.body);
        return PlotAllocationResponse.fromJson(responseData);
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['detail'] ?? 'Bad request');
      } else if (response.statusCode == 404) {
        throw Exception('Estate not found');
      } else {
        throw Exception('Failed to load plots (${response.statusCode})');
      }
    } catch (e) {
      rethrow;
    }
  }

  Future<void> createAllocation({
    required int clientId,
    required int estateId,
    required int plotSizeUnitId,
    int? plotNumberId,
    required String paymentType,
    required String token,
  }) async {
    final uri = Uri.parse('$baseUrl/update-allocation/');

    final body = {
      'client_id': clientId,
      'estate_id': estateId,
      'plot_size_unit_id': plotSizeUnitId,
      'payment_type': paymentType,
      if (paymentType == 'full') 'plot_number_id': plotNumberId!,
    };

    final response = await http.post(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode(body),
    );

    if (response.statusCode != 201) {
      final data = jsonDecode(response.body);
      final err =
          data['errors'] ?? data['message'] ?? 'Failed to allocate plot';
      throw Exception(err.toString());
    }
  }

  //? ADD ESTATE
  Future<Map<String, dynamic>> addEstate({
    required String token,
    required String estateName,
    required String location,
    required String estateSize,
    required String titleDeed,
  }) async {
    final url = Uri.parse('$baseUrl/add-estate/');

    final response = await http.post(
      url,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: jsonEncode({
        // These keys must match your Django EstateSerializer fields:
        'name': estateName,
        'location': location,
        'estate_size': estateSize,
        'title_deed': titleDeed,
      }),
    );

    if (response.statusCode == 201) {
      return {'success': true, 'message': 'Estate added successfully.'};
    } else {
      try {
        final data = jsonDecode(response.body);
        // serializer errors come back under 'error'
        final err = data['error'] ?? data;
        return {'success': false, 'message': err.toString()};
      } catch (_) {
        return {'success': false, 'message': 'Unknown error occurred.'};
      }
    }
  }

  // ---------------- PLOT SIZE METHODS ----------------

  Future<List<AddPlotSize>> fetchPlotSizes(String token) async {
    final response = await http.get(
      Uri.parse('$baseUrl/plot-sizes/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.map((e) => AddPlotSize.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load plot sizes: ${response.statusCode}');
    }
  }

  Future<AddPlotSize> createPlotSize(String size, String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/plot-sizes/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({'size': size}),
    );

    if (response.statusCode == 201) {
      return AddPlotSize.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create plot size: ${response.statusCode}');
    }
  }

  Future<void> deletePlotSize(int id, String token) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/plot-sizes/$id/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 204) {
      throw Exception('Failed to delete plot size: ${response.statusCode}');
    }
  }

  Future<void> updatePlotSize(int id, String newSize, String token) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/plot-sizes/$id/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({'size': newSize}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update plot size: ${response.statusCode}');
    }
  }

  // ---------------- PLOT NUMBER METHODS ----------------

  // Plot Numbers API Calls
  Future<List<AddPlotNumber>> fetchPlotNumbers(String token,
      {int page = 1, int perPage = 50}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/plot-numbers/?page=$page&per_page=$perPage'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      List<dynamic> data = json.decode(response.body);
      return data.map((e) => AddPlotNumber.fromJson(e)).toList();
    } else {
      throw Exception('Failed to load plot numbers: ${response.statusCode}');
    }
  }

  Future<AddPlotNumber> createPlotNumber(String number, String token) async {
    final response = await http.post(
      Uri.parse('$baseUrl/plot-numbers/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({'number': number}),
    );

    if (response.statusCode == 201) {
      return AddPlotNumber.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to create plot number: ${response.statusCode}');
    }
  }

  Future<void> deletePlotNumber(int id, String token) async {
    final response = await http.delete(
      Uri.parse('$baseUrl/plot-numbers/$id/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode != 204) {
      throw Exception('Failed to delete plot number: ${response.statusCode}');
    }
  }

  Future<void> updatePlotNumber(int id, String newNumber, String token) async {
    final response = await http.patch(
      Uri.parse('$baseUrl/plot-numbers/$id/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({'number': newNumber}),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to update plot number: ${response.statusCode}');
    }
  }

  // ADMIN CLIENT CHAT LIST
  Future<List<Chat>> fetchClientChats(String token) async {
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/admin-support/client-chats/'),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        if (data.isEmpty) {
          if (kDebugMode) {}
          return [];
        }
        return data.map((chatJson) => Chat.fromJson(chatJson)).toList();
      } else {
        final errorMsg =
            'Failed to load client chats: ${response.statusCode} - ${response.body}';
        if (kDebugMode) {}
        throw Exception(errorMsg);
      }
    } catch (e) {
      if (kDebugMode) {}
      rethrow;
    }
  }

  Future<List<Message>> fetchChatThread(String token, String clientId) async {
    final response = await http.get(
      Uri.parse('$baseUrl/client-chats/$clientId/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final List data = jsonDecode(response.body);
      return data.map((msgJson) => Message.fromJson(msgJson)).toList();
    } else {
      throw Exception('Failed to load thread: ${response.statusCode}');
    }
  }

  Future<Message> sendAdminMessage({
    required String token,
    required String clientId,
    required String content,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/client-chats/$clientId/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({'content': content, 'message_type': 'enquiry'}),
    );

    if (response.statusCode == 201) {
      return Message.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to send message: ${response.statusCode}');
    }
  }

  requestPasswordReset(String mail) {}

  // CLIENT SIDE

  // Client dashboard
  Map<String, dynamic>? _normalizePromo(dynamic promo) {
    if (promo == null) return null;
    if (promo is! Map<String, dynamic>) return null;

    // Ensure discount_pct exists
    if (!promo.containsKey('discount_pct') && promo.containsKey('discount')) {
      final d = promo['discount'];
      if (d is num) {
        promo['discount_pct'] = d.round();
      } else {
        final parsed = int.tryParse(d?.toString() ?? '');
        if (parsed != null) promo['discount_pct'] = parsed;
      }
    }

    // Ensure active exists (compute from start/end using date-only comparison)
    if (!promo.containsKey('active')) {
      try {
        final sStr = promo['start']?.toString();
        final eStr = promo['end']?.toString();
        if (sStr != null && eStr != null) {
          final start = DateTime.tryParse(sStr);
          final end = DateTime.tryParse(eStr);
          if (start != null && end != null) {
            final now = DateTime.now();
            final today = DateTime(now.year, now.month, now.day);
            final startDate = DateTime(start.year, start.month, start.day);
            final endDate = DateTime(end.year, end.month, end.day);
            promo['active'] =
                !today.isBefore(startDate) && !today.isAfter(endDate);
          } else {
            promo['active'] = false;
          }
        } else {
          promo['active'] = false;
        }
      } catch (e) {
        promo['active'] = false;
      }
    }

    // Defensive: normalize nested estates -> company_logo and sizes (promo_price/discount_pct)
    if (promo['estates'] is List) {
      promo['estates'] = (promo['estates'] as List).map((e) {
        if (e is Map<String, dynamic>) {
          final company = e['company'];
          if (company is Map<String, dynamic>) {
            final cand = company['company_logo'] ??
                company['logo'] ??
                company['logo_url'] ??
                (company['logo'] is Map
                    ? (company['logo'] as Map<String, dynamic>)['url']
                    : null);
            if (cand is String && cand.isNotEmpty)
              company['company_logo'] = _absUrl(cand);
            e['company'] = company;
          } else {
            final cand = e['company_logo'] ?? e['logo'];
            if (cand is String && cand.isNotEmpty)
              e['company_logo'] = _absUrl(cand);
          }

          if (e['sizes'] is List) {
            e['sizes'] = (e['sizes'] as List).map((s) {
              if (s is Map<String, dynamic>) {
                s['promo_price'] = s['promo_price'] ??
                    s['promoPrice'] ??
                    s['price'] ??
                    s['current'];
                s['discount_pct'] = s['discount_pct'] ??
                    s['discount'] ??
                    promo['discount_pct'] ??
                    null;
              }
              return s;
            }).toList();
          }
        }
        return e;
      }).toList();
    }

    return promo;
  }

  /// Fetch complete client dashboard data with stats, promotions, and price history
  /// Endpoint: GET /api/client/dashboard/
  /// Returns: user, stats (4 cards), active_promotions, latest_value_by_company organized by company
  Future<Map<String, dynamic>> getClientDashboardData(String token) async {
    final url = '$baseUrl/api/client/dashboard/';
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Authorization': 'Token $token'
    };
    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;

      // Normalize any promos in active_promotions
      if (data['active_promotions'] is List) {
        for (var i = 0; i < (data['active_promotions'] as List).length; i++) {
          final item = data['active_promotions'][i];
          if (item is Map<String, dynamic>) {
            _normalizePromo(item);
            // also normalize nested estates[].sizes if present
            if (item.containsKey('estates') && item['estates'] is List) {
              for (var e in item['estates']) {
                if (e is Map<String, dynamic> &&
                    e.containsKey('sizes') &&
                    e['sizes'] is List) {
                  for (var s in e['sizes']) {
                    if (s is Map<String, dynamic>) {
                      // ensure discount_pct on the size too if needed
                      if (!s.containsKey('discount_pct') &&
                          s.containsKey('current') &&
                          item.containsKey('discount_pct')) {
                        // compute discounted with server-provided discount_pct if missing
                        final cur = s['current'];
                        final disc = item['discount_pct'];
                        if (cur != null && disc is num) {
                          final promoPrice =
                              (cur is num) ? (cur * (100 - disc) / 100) : null;
                          s['promo_price'] = promoPrice;
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }

      // Normalize promos in latest_value_by_company (organized by company for accordion)
      if (data['latest_value_by_company'] is List) {
        for (var companyGroup in data['latest_value_by_company']) {
          if (companyGroup is Map<String, dynamic> &&
              companyGroup['updates'] is List) {
            for (var update in companyGroup['updates']) {
              if (update is Map<String, dynamic> &&
                  update.containsKey('promo')) {
                update['promo'] = _normalizePromo(update['promo']);
              }
            }
          }
        }
      }

      return data;
    } else {
      throw Exception(
          'Failed to load dashboard data: ${resp.statusCode} ${resp.body}');
    }
  }

  /// Fetch detailed price update by ID
  /// Endpoint: GET /api/price-update/<id>/
  /// Returns: PriceHistory with estate, plot_unit, prices, percent_change, promo, dates
  Future<Map<String, dynamic>> getPriceUpdateById(int id,
      {String? token, Duration timeout = const Duration(seconds: 15)}) async {
    final url = '$baseUrl/api/price-update/$id/';
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty)
      headers['Authorization'] = 'Token $token';
    final resp =
        await http.get(Uri.parse(url), headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;
      if (data.containsKey('promo'))
        data['promo'] = _normalizePromo(data['promo']);
      return data;
    } else {
      throw Exception(
          'Failed to load price update: ${resp.statusCode} ${resp.body}');
    }
  }

  /// Fetch active promotional offers for user's affiliated companies
  /// Endpoint: GET /api/active-promotions/
  /// Returns: List of active promotions with estates and pricing
  Future<List<Map<String, dynamic>>> getActivePromotions(
      {String? token, Duration timeout = const Duration(seconds: 15)}) async {
    final url = '$baseUrl/api/active-promotions/';
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty)
      headers['Authorization'] = 'Token $token';
    final resp =
        await http.get(Uri.parse(url), headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final dynamic decoded = jsonDecode(resp.body);
      if (decoded is List) {
        final promos = <Map<String, dynamic>>[];
        for (var p in decoded) {
          if (p is Map<String, dynamic>) {
            _normalizePromo(p);
            promos.add(p);
          }
        }
        return promos;
      } else if (decoded is Map && decoded['data'] is List) {
        final promos = <Map<String, dynamic>>[];
        for (var p in decoded['data']) {
          if (p is Map<String, dynamic>) {
            _normalizePromo(p);
            promos.add(p);
          }
        }
        return promos;
      }
      return [];
    } else {
      throw Exception(
          'Failed to load active promotions: ${resp.statusCode} ${resp.body}');
    }
  }

  /// Fetch paginated promotions with filtering
  /// Endpoint: GET /api/promotions/?filter=all|active|past&page=X&q=search
  /// Returns: {active_promotions: [...], promotions: {count, next, previous, results: [...]}}
  Future<Map<String, dynamic>> listPromotions({
    String? token,
    String filter = 'all',
    String? q,
    int page = 1,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final qPart =
        q != null && q.isNotEmpty ? '&q=${Uri.encodeQueryComponent(q)}' : '';
    final url =
        '$baseUrl/api/promotions/?filter=${Uri.encodeQueryComponent(filter)}&page=$page$qPart';
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty)
      headers['Authorization'] = 'Token $token';
    final resp =
        await http.get(Uri.parse(url), headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;

      // Normalize active_promotions (list)
      if (data['active_promotions'] is List) {
        for (var i = 0; i < (data['active_promotions'] as List).length; i++) {
          final p = data['active_promotions'][i];
          if (p is Map<String, dynamic>) _normalizePromo(p);
        }
      }

      // Normalize paginated promotions -> results
      if (data['promotions'] is Map && data['promotions']['results'] is List) {
        for (var i = 0;
            i < (data['promotions']['results'] as List).length;
            i++) {
          final p = data['promotions']['results'][i];
          if (p is Map<String, dynamic>) _normalizePromo(p);
        }
      }

      return data;
    } else {
      throw Exception(
          'Failed to load promotions: ${resp.statusCode} ${resp.body}');
    }
  }

  /// Fetch detailed promotion information
  /// Endpoint: GET /api/promotion/<id>/
  /// Returns: Complete promotion with estates, sizes, pricing, and active status
  Future<Map<String, dynamic>> getPromotionDetail(int id,
      {String? token, Duration timeout = const Duration(seconds: 15)}) async {
    final url = '$baseUrl/api/promotion/$id/';
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token != null && token.isNotEmpty)
      headers['Authorization'] = 'Token $token';
    final resp =
        await http.get(Uri.parse(url), headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;

      // top-level promo object fields (depending on serializer shape)
      _normalizePromo(data);

      // normalize nested estates -> sizes
      if (data['estates'] is List) {
        for (var est in data['estates']) {
          if (est is Map<String, dynamic> && est['sizes'] is List) {
            for (var s in est['sizes']) {
              if (s is Map<String, dynamic>) {
                if (!s.containsKey('discount_pct') &&
                    data.containsKey('discount_pct')) {
                  final disc = data['discount_pct'];
                  if (disc is num) s['discount_pct'] = disc.round();
                }
              }
            }
          }
        }
      }

      return data;
    } else {
      throw Exception(
          'Failed to load promotion detail: ${resp.statusCode} ${resp.body}');
    }
  }

  Future<Map<String, dynamic>> getClientProfile({required String token}) async {
    final url = '$baseUrl/users/me/';
    final headers = <String, String>{
      'Content-Type': 'application/json',
      'Authorization': 'Token $token'
    };
    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      final Map<String, dynamic> data = (decoded is Map<String, dynamic> &&
              decoded.containsKey('data') &&
              decoded['success'] == true &&
              decoded['data'] is Map<String, dynamic>)
          ? Map<String, dynamic>.from(decoded['data'])
          : (decoded is Map<String, dynamic>
              ? Map<String, dynamic>.from(decoded)
              : <String, dynamic>{});

      // inline normalize helper (recursively normalizes profile_image / image-like fields)
      void _normalizeMediaUrlsInMap(Map<String, dynamic> m) {
        m.forEach((k, v) {
          if (v is String) {
            // check common media keys
            if ((k.toLowerCase().contains('image') ||
                    k.toLowerCase().contains('photo') ||
                    k.toLowerCase().contains('avatar')) &&
                v.isNotEmpty &&
                !v.startsWith('http')) {
              m[k] = '$baseUrl$v';
            }
          } else if (v is Map<String, dynamic>) {
            _normalizeMediaUrlsInMap(v);
          } else if (v is List) {
            for (var i = 0; i < v.length; i++) {
              final item = v[i];
              if (item is Map<String, dynamic>) {
                _normalizeMediaUrlsInMap(item);
              } else if (item is String) {
                // if list contains string paths (rare), try normalize
                if (item.isNotEmpty && !item.startsWith('http')) {
                  v[i] = '$baseUrl$item';
                }
              }
            }
          }
        });
      }

      _normalizeMediaUrlsInMap(data);
      return data;
    } else {
      throw Exception(
          'Failed to load profile: ${resp.statusCode} ${resp.body}');
    }
  }

  /// Fetch paginated list of estates for user's affiliated companies
  /// Endpoint: GET /api/estates/?page=X&q=search&estate_id=X
  /// Returns: List of estates with details, promos, and pricing
  Future<Map<String, dynamic>> listEstates({
    String? token,
    int page = 1,
    String? q,
    int? estateId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final qPart =
        q != null && q.isNotEmpty ? '&q=${Uri.encodeQueryComponent(q)}' : '';
    final estatePart = estateId != null ? '&estate_id=$estateId' : '';
    final url = '$baseUrl/api/estates/?page=$page$qPart$estatePart';
    final headers = <String, String>{
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Token $token',
    };

    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode != 200) {
      throw Exception(
          'Failed to list estates: ${resp.statusCode} ${resp.body}');
    }
    final dynamic decoded = jsonDecode(resp.body);

    // DEBUG: Log raw response
    debugPrint('📥 API listEstates response status: ${resp.statusCode}');
    debugPrint('📥 Response body length: ${resp.body.length} chars');

    // If server returned a plain list, wrap it
    if (decoded is List) {
      final list = List<dynamic>.from(decoded);
      // ensure each estate is a Map
      final normalized = list.map((e) {
        if (e is Map) return Map<String, dynamic>.from(e);
        return {'id': null, 'name': e?.toString()};
      }).toList();
      return {
        'results': normalized,
        'count': normalized.length,
        'next': null,
        'previous': null,
        'total_pages': 1,
      };
    }

    if (decoded is Map<String, dynamic>) {
      // common paginated case
      if (decoded.containsKey('results') && decoded['results'] is List) {
        final results = (decoded['results'] as List).map((e) {
          if (e is Map) {
            final estateMap = Map<String, dynamic>.from(e);
            // DEBUG: Check if promotional_offers exists
            if (estateMap.containsKey('promotional_offers')) {
              final promos = estateMap['promotional_offers'];
              debugPrint(
                  '✅ Estate "${estateMap['name']}": has promotional_offers (${promos is List ? promos.length : 0})');
              if (promos is List && promos.isNotEmpty) {
                debugPrint('   First promo: ${promos[0]}');
              }
            } else {
              debugPrint(
                  '❌ Estate "${estateMap['name']}": NO promotional_offers field!');
              debugPrint('   Available keys: ${estateMap.keys.toList()}');
            }
            return estateMap;
          }
          return {'id': null, 'name': e?.toString()};
        }).toList();

        debugPrint('📦 Returning ${results.length} estates from API');

        final out = Map<String, dynamic>.from(decoded);
        out['results'] = results;
        return out;
      } else {
        // maybe single object (coerce to results)
        if (decoded.containsKey('id') || decoded.containsKey('name')) {
          return {
            'results': [decoded],
            'count': 1,
            'next': null,
            'previous': null,
            'total_pages': 1,
          };
        }
        // unexpected map
        return {
          'results': [],
          'count': 0,
          'next': null,
          'previous': null,
          'total_pages': 1,
        };
      }
    }

    // fallback
    return {
      'results': [],
      'count': 0,
      'next': null,
      'previous': null,
      'total_pages': 1,
    };
  }

  /// Fetch currently active promotional offers
  Future<List<dynamic>> listActivePromotions(
      {String? token, Duration timeout = const Duration(seconds: 15)}) async {
    final url = '$baseUrl/api/active-promotions/';
    final headers = <String, String>{
      'Content-Type': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Token $token',
    };

    final resp =
        await http.get(Uri.parse(url), headers: headers).timeout(timeout);
    if (resp.statusCode != 200) {
      throw Exception(
          'Failed to load active promotions: ${resp.statusCode} ${resp.body}');
    }
    final dynamic decoded = jsonDecode(resp.body);
    if (decoded is List) {
      return decoded
          .map((e) => e is Map ? Map<String, dynamic>.from(e) : e)
          .toList();
    }
    return [];
  }

  Future<Map<String, dynamic>> getEstateModalJson(int estateId,
      {String? token}) async {
    final url = '$baseUrl/estates/?estate_id=$estateId';
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      if (token != null && token.isNotEmpty) 'Authorization': 'Token $token',
    };

    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode != 200) {
      throw Exception(
          'Failed to load estate info: ${resp.statusCode} ${resp.body}');
    }

    dynamic decoded;
    try {
      decoded = jsonDecode(resp.body);
    } catch (e) {
      throw Exception('Invalid JSON from server for estate $estateId: $e');
    }

    // If server returned a map with sizes/promo, normalize directly
    if (decoded is Map) {
      final Map<String, dynamic> m = Map<String, dynamic>.from(decoded);

      // if m has 'results' (list), find possible item
      if (m['results'] is List) {
        final list = (m['results'] as List)
            .whereType<Map>()
            .map((e) => Map<String, dynamic>.from(e))
            .toList();
        if (list.isNotEmpty) {
          final found = list.firstWhere(
            (e) {
              try {
                final dynamic idA = e['id'] ?? e['estate_id'];
                if (idA == null) return false;
                // compare both as ints and as strings (defensive)
                if (idA is num && idA.toInt() == estateId) return true;
                if (idA is String && idA == estateId.toString()) return true;
                return false;
              } catch (_) {
                return false;
              }
            },
            orElse: () => list.first,
          );

          return _normalizeEstateModalFromServer(found, estateId);
        }
      }

      // server gave single estate map (likely contains sizes/promo)
      return _normalizeEstateModalFromServer(m, estateId);
    }

    // If server returned a list, treat as sizes
    if (decoded is List) {
      final sizes = decoded.map((s) {
        if (s is Map) {
          return Map<String, dynamic>.from(s);
        }
        return {'size': s?.toString(), 'amount': null};
      }).toList();
      return {
        'estate_id': estateId,
        'estate_name': null,
        'promo': null,
        'sizes': sizes,
      };
    }

    // fallback empty
    return {
      'estate_id': estateId,
      'estate_name': null,
      'promo': null,
      'sizes': [],
    };
  }

  Map<String, dynamic> _normalizeEstateModalFromServer(
      Map<String, dynamic> raw, int estateId) {
    final out = <String, dynamic>{};

    out['estate_id'] = raw['estate_id'] ?? raw['id'] ?? estateId;
    out['estate_name'] = raw['estate_name'] ??
        raw['name'] ??
        (raw['estate'] is Map ? raw['estate']['name'] : null);

    // promo normalization
    if (raw['promo'] is Map) {
      final p = Map<String, dynamic>.from(raw['promo']);
      if (!p.containsKey('discount_pct') && p.containsKey('discount')) {
        final d = p['discount'];
        if (d is num) {
          p['discount_pct'] = d.toInt();
        } else {
          final parsed = int.tryParse(d?.toString() ?? '');
          if (parsed != null) p['discount_pct'] = parsed;
        }
      }
      out['promo'] = p;
    } else if (raw['promotion'] is Map) {
      out['promo'] = Map<String, dynamic>.from(raw['promotion']);
    } else {
      out['promo'] = raw['promo'] ?? null;
    }

    // sizes normalization (accept many shapes)
    final rawSizes = <dynamic>[];
    if (raw['sizes'] is List) rawSizes.addAll(raw['sizes']);
    if (raw['property_prices'] is List) rawSizes.addAll(raw['property_prices']);
    if (raw['results'] is List) rawSizes.addAll(raw['results']);

    final sizes = <Map<String, dynamic>>[];
    for (var s in rawSizes) {
      if (s is Map) {
        // nested-safe extraction of size name
        String? sizeName;
        final dynamic sizeVal = s['size'] ?? s['plot_size'];
        if (sizeVal != null) {
          sizeName = sizeVal.toString();
        } else {
          final plotUnit = s['plot_unit'];
          if (plotUnit is Map) {
            final plotSize = plotUnit['plot_size'];
            if (plotSize is Map && plotSize['size'] != null) {
              sizeName = plotSize['size'].toString();
            }
          }
        }

        // amount
        double? amount;
        if (s.containsKey('amount')) {
          final a = s['amount'];
          amount =
              (a is num) ? a.toDouble() : double.tryParse(a?.toString() ?? '');
        }
        if (amount == null && s.containsKey('current')) {
          final a = s['current'];
          amount =
              (a is num) ? a.toDouble() : double.tryParse(a?.toString() ?? '');
        }

        // discounted / promo price
        double? discounted;
        if (s.containsKey('discounted')) {
          final d = s['discounted'];
          discounted =
              (d is num) ? d.toDouble() : double.tryParse(d?.toString() ?? '');
        }
        if (discounted == null && s.containsKey('promo_price')) {
          final d = s['promo_price'];
          discounted =
              (d is num) ? d.toDouble() : double.tryParse(d?.toString() ?? '');
        }

        // discount percent
        int? discountPct;
        final dp = s['discount_pct'] ?? s['discount'];
        if (dp != null) {
          if (dp is num)
            discountPct = dp.toInt();
          else
            discountPct = int.tryParse(dp.toString());
        }

        sizes.add({
          'plot_unit_id': s['plot_unit_id'] ??
              (s['plot_unit'] is Map ? s['plot_unit']['id'] : null),
          'size': sizeName,
          'amount': amount,
          'discounted': discounted,
          'discount_pct': discountPct,
        });
      } else {
        sizes.add({
          'size': s?.toString(),
          'amount': null,
          'discounted': null,
          'discount_pct': null
        });
      }
    }

    // Apply estate-level promo to sizes that don't have their own discount
    if (out['promo'] is Map) {
      final promo = out['promo'] as Map<String, dynamic>;
      final isActive = promo['active'] == true || promo['is_active'] == true;
      if (isActive) {
        final estateDiscountPct = promo['discount_pct'] ?? promo['discount'];
        int? estateDiscount;
        if (estateDiscountPct is num) {
          estateDiscount = estateDiscountPct.toInt();
        } else if (estateDiscountPct != null) {
          estateDiscount = int.tryParse(estateDiscountPct.toString());
        }

        if (estateDiscount != null && estateDiscount > 0) {
          for (var size in sizes) {
            // Only apply if size doesn't already have a discount
            if (size['discounted'] == null && size['amount'] != null) {
              final amount = size['amount'] as double;
              final discountedPrice = amount * (100 - estateDiscount) / 100;
              size['discounted'] = discountedPrice;
              size['discount_pct'] = estateDiscount;
            }
          }
        }
      }
    }

    // normalize company logo (accept several server shapes)
    String? _companyLogo;
    if (raw['company'] is Map<String, dynamic>) {
      final company = Map<String, dynamic>.from(raw['company']);
      final cand = company['company_logo'] ??
          company['logo'] ??
          company['logo_url'] ??
          (company['logo'] is Map
              ? (company['logo'] as Map<String, dynamic>)['url']
              : null);
      if (cand is String && cand.isNotEmpty) {
        company['company_logo'] = _absUrl(cand);
      }
      out['company'] = company;
      _companyLogo = company['company_logo'];
    } else {
      final cand = raw['company_logo'] ?? raw['logo'];
      out['company_logo'] =
          cand is String && cand.isNotEmpty ? _absUrl(cand) : null;
      _companyLogo = out['company_logo'];
    }

    // ensure sizes exist and return
    out['sizes'] = sizes;
    return out;
  }

  /// Update client profile
  Future<void> updateClientProfileMultipart({
    required String token,
    File? profileImage,
    Map<String, String>? fields,
  }) async {
    final dio = Dio();
    final url = '$baseUrl/clients/profile/update/';
    try {
      final formData = FormData();

      fields?.forEach((k, v) {
        if (v.isNotEmpty) formData.fields.add(MapEntry(k, v));
      });

      if (profileImage != null) {
        final fileName = profileImage.path.split('/').last;
        formData.files.add(MapEntry(
          'profile_image',
          await MultipartFile.fromFile(profileImage.path, filename: fileName),
        ));
      }

      final response = await dio.post(url,
          data: formData,
          options: Options(headers: {'Authorization': 'Token $token'}));
      if (response.statusCode != 200 && response.statusCode != 201) {
        throw Exception('Failed to update profile: ${response.statusCode}');
      }
    } catch (e) {
      rethrow;
    }
  }

  Future<List<dynamic>> getClientClientProperties(
      {required String token}) async {
    final url = '$baseUrl/clients/properties/';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      final list = jsonDecode(resp.body) as List<dynamic>;
      return list;
    } else {
      throw Exception('Failed to load client properties');
    }
  }

  Future<Map<String, dynamic>> getClientAppreciation(
      {required String token}) async {
    final url = '$baseUrl/clients/appreciation/';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load appreciation data');
    }
  }

  Future<void> changeClientPassword({
    required String token,
    required String currentPassword,
    required String newPassword,
  }) async {
    final url = '$baseUrl/clients/change-password/';
    final resp = await http.post(Uri.parse(url),
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Token $token',
        },
        body: jsonEncode({
          'current_password': currentPassword,
          'new_password': newPassword
        }));
    if (resp.statusCode != 200) {
      throw Exception('Failed to change password: ${resp.body}');
    }
  }

  Future<List<dynamic>> getClientClientTransactions(
      {required String token}) async {
    final url = '$baseUrl/clients/transactions/';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as List<dynamic>;
    } else {
      throw Exception('Failed to load transactions: ${resp.statusCode}');
    }
  }

  Future<Map<String, dynamic>> getTransactionDetails({
    required int transactionId,
    required String token,
  }) async {
    final url = '$baseUrl/clients/transaction/$transactionId/details/';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    } else {
      throw Exception('Failed to load transaction details: ${resp.statusCode}');
    }
  }

  Future<List<dynamic>> getClientTransactionPayments({
    required int transactionId,
    required String token,
  }) async {
    final url =
        '$baseUrl/clients/transaction/payments/?transaction_id=$transactionId';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as List<dynamic>;
    } else {
      throw Exception(
          'Failed to load transaction payments: ${resp.statusCode}');
    }
  }

  Future<void> downloadPaymentReceiptAndOpen({
    required String reference,
    required String token,
    String filename = 'receipt.pdf',
  }) async {
    final url = '$baseUrl/payment/receipt/$reference/';
    final resp = await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
    if (resp.statusCode == 200) {
      final contentType = resp.headers['content-type'] ?? '';
      if (contentType.contains('application/pdf') ||
          resp.bodyBytes.isNotEmpty) {
        final tempDir = await getTemporaryDirectory();
        final file = File('${tempDir.path}/$filename');
        await file.writeAsBytes(resp.bodyBytes);
        await OpenFile.open(file.path);
      } else {
        // assume JSON with url or base64
        final js = jsonDecode(resp.body);
        if (js['url'] != null) {
          final pdfResp = await http.get(Uri.parse(js['url']));
          final tempDir = await getTemporaryDirectory();
          final file = File('${tempDir.path}/$filename');
          await file.writeAsBytes(pdfResp.bodyBytes);
          await OpenFile.open(file.path);
        } else {
          throw Exception('Unsupported receipt format');
        }
      }
    } else {
      throw Exception('Failed to download receipt: ${resp.statusCode}');
    }
  }

  Future<http.Response> downloadTransactionReceiptRaw({
    required int transactionId,
    required String token,
  }) async {
    final url = '$baseUrl/transaction/$transactionId/receipt/';
    return await http.get(Uri.parse(url), headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Token $token',
    });
  }

  void _normalizeMediaUrls(Map<String, dynamic> data) {
    // shallow normalization for common keys (accept company logo variants)
    final keys = [
      'profile_image',
      'image',
      'avatar',
      'photo',
      'company_logo',
      'logo'
    ];
    for (final k in keys) {
      if (!data.containsKey(k) || data[k] == null) continue;
      final v = data[k];
      if (v is String && v.isNotEmpty) {
        data[k] = _absUrl(v);
      } else if (v is Map<String, dynamic>) {
        final candidate = v['url'] ?? v['path'] ?? v['logo'] ?? v['logo_url'];
        if (candidate is String && candidate.isNotEmpty)
          data[k] = _absUrl(candidate);
      }
    }

    // normalize nested company.logo / company.company_logo
    if (data['company'] is Map<String, dynamic>) {
      final company = data['company'] as Map<String, dynamic>;
      final cand = company['company_logo'] ??
          company['logo'] ??
          company['logo_url'] ??
          (company['logo'] is Map
              ? (company['logo'] as Map<String, dynamic>)['url']
              : null);
      if (cand is String && cand.isNotEmpty)
        company['company_logo'] = _absUrl(cand);
      data['company'] = company;
    }
  }

  /// Estate plot details Views
  Future<Map<String, dynamic>> fetchClientEstatePlotDetail({
    required int estateId,
    required String token,
    int? plotSizeId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final clientPath = Uri.parse('$baseUrl/clients/estates/$estateId/').replace(
        queryParameters:
            plotSizeId != null ? {'plot_size': plotSizeId.toString()} : null);
    final canonicalPath = Uri.parse('$baseUrl/estates/$estateId/').replace(
        queryParameters:
            plotSizeId != null ? {'plot_size': plotSizeId.toString()} : null);

    Future<http.Response> _get(Uri uri) {
      return http.get(uri, headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      }).timeout(timeout);
    }

    http.Response resp;
    try {
      resp = await _get(clientPath);
      if (resp.statusCode == 404) {
        // try canonical
        resp = await _get(canonicalPath);
      }
    } on Exception {
      // network/timeout -> rethrow to be handled by callers
      rethrow;
    }

    // now handle resp as you already do: check status codes, decode, normalize, etc.
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;
      // (run your normalize steps here)
      return data;
    }

    // existing error handling...
    switch (resp.statusCode) {
      case 404:
        throw Exception('Estate not found (404).');
      case 401:
        throw Exception('Authentication failed. Please re-login (401).');
      case 403:
        throw Exception('Permission denied (403).');
      case 500:
        throw Exception('Server error (500). Try again later.');
      default:
        throw Exception(
            'Failed to load estate detail: ${resp.statusCode} - ${resp.body}');
    }
  }

  // PROFILE METHODS
  Future<Map<String, dynamic>> getClientProfileOverview({
    required String token,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/profile/overview/');

    final resp = await http.get(uri, headers: {
      'Authorization': 'Token $token',
      'Accept': 'application/json',
    }).timeout(timeout);

    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }

    String msg = 'Failed to load profile overview: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<Map<String, dynamic>> getClientDetailByToken({
    required String token,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/profile/');

    final resp = await http.get(uri, headers: {
      'Authorization': 'Token $token',
      'Accept': 'application/json',
    }).timeout(timeout);

    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }

    String msg = 'Failed to load profile: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<Map<String, dynamic>> updateClientProfileByToken({
    required String token,
    String? title,
    String? fullName,
    String? about,
    String? dateOfBirth,
    String? company,
    String? job,
    String? country,
    String? address,
    String? phone,
    File? profileImage,
    Duration timeout = const Duration(seconds: 40),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/profile/');
    final request = http.MultipartRequest('POST', uri);

    // Headers
    request.headers['Authorization'] = 'Token $token';
    request.headers['Accept'] = 'application/json';

    // Add optional fields (only non-null, non-empty values)
    if (title != null && title.trim().isNotEmpty)
      request.fields['title'] = title;
    if (fullName != null && fullName.trim().isNotEmpty)
      request.fields['full_name'] = fullName;
    if (about != null && about.trim().isNotEmpty)
      request.fields['about'] = about;
    if (dateOfBirth != null && dateOfBirth.trim().isNotEmpty)
      request.fields['date_of_birth'] = dateOfBirth;
    if (company != null && company.trim().isNotEmpty)
      request.fields['company'] = company;
    if (job != null && job.trim().isNotEmpty) request.fields['job'] = job;
    if (country != null && country.trim().isNotEmpty)
      request.fields['country'] = country;
    if (address != null && address.trim().isNotEmpty)
      request.fields['address'] = address;
    if (phone != null && phone.trim().isNotEmpty)
      request.fields['phone'] = phone;

    // Attach profile image if provided (multipart form data)
    if (profileImage != null) {
      final mimeType = lookupMimeType(profileImage.path) ?? 'image/jpeg';
      request.files.add(
        await http.MultipartFile.fromPath(
          'profile_image',
          profileImage.path,
          contentType: MediaType.parse(mimeType),
        ),
      );
    }

    final streamed = await request.send().timeout(timeout);
    final resp = await http.Response.fromStream(streamed);

    if (resp.statusCode == 200 || resp.statusCode == 201) {
      if (resp.body.isEmpty) return <String, dynamic>{};
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }

    String msg = 'Failed to update profile: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<Map<String, dynamic>> uploadClientProfileImage({
    required String token,
    required File profileImage,
    Duration timeout = const Duration(seconds: 30),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/profile/image/');
    final request = http.MultipartRequest('POST', uri);

    request.headers['Authorization'] = 'Token $token';
    request.headers['Accept'] = 'application/json';

    final mimeType = lookupMimeType(profileImage.path) ?? 'image/jpeg';
    request.files.add(
      await http.MultipartFile.fromPath(
        'profile_image',
        profileImage.path,
        contentType: MediaType.parse(mimeType),
      ),
    );

    final streamed = await request.send().timeout(timeout);
    final resp = await http.Response.fromStream(streamed);

    if (resp.statusCode == 200 || resp.statusCode == 201) {
      if (resp.body.isEmpty) return <String, dynamic>{};
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }

    String msg = 'Failed to upload profile image: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<void> changePasswordByToken({
    required String token,
    required String currentPassword,
    required String newPassword,
    required String confirmPassword,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/change-password/');

    // Validate input on client side before sending
    if (newPassword != confirmPassword) {
      throw Exception('New password and confirmation do not match');
    }

    final resp = await http
        .post(
          uri,
          headers: {
            'Authorization': 'Token $token',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: jsonEncode({
            'current_password': currentPassword,
            'new_password': newPassword,
            'confirm_password': confirmPassword,
          }),
        )
        .timeout(timeout);

    if (resp.statusCode == 200 || resp.statusCode == 204) return;

    String message = 'Failed to change password: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map) {
        if (j['detail'] != null) message = j['detail'].toString();
        if (j['current_password'] != null)
          message = 'Current password is incorrect';
        if (j['new_password'] != null) message = j['new_password'].toString();
      }
    } catch (_) {}
    throw Exception('$message ${resp.body}');
  }

  Future<Map<String, dynamic>> getTransactionDetail({
    required String token,
    required int transactionId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri =
        Uri.parse('$baseUrl/clients/transaction/$transactionId/details/');

    final resp = await http.get(uri, headers: {
      'Authorization': 'Token $token',
      'Accept': 'application/json',
    }).timeout(timeout);

    if (resp.statusCode == 200) {
      return jsonDecode(resp.body) as Map<String, dynamic>;
    }

    String msg = 'Failed to load transaction: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<List<dynamic>> getTransactionPayments({
    required String token,
    required int transactionId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse(
        '$baseUrl/clients/transaction/payments/?transaction_id=$transactionId');

    final resp = await http.get(uri, headers: {
      'Authorization': 'Token $token',
      'Accept': 'application/json',
    }).timeout(timeout);

    if (resp.statusCode == 200) {
      final Map<String, dynamic> body =
          jsonDecode(resp.body) as Map<String, dynamic>;
      return (body['payments'] as List<dynamic>);
    }

    String msg = 'Failed to load payments: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<List<dynamic>> fetchTransactionPaymentsApi({
    required String token,
    required int transactionId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/transaction/payments/')
        .replace(queryParameters: {'transaction_id': transactionId.toString()});

    final resp = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Accept': 'application/json',
      },
    ).timeout(timeout);

    if (resp.statusCode == 200) {
      final Map<String, dynamic> body =
          jsonDecode(resp.body) as Map<String, dynamic>;
      final payments = body['payments'] as List<dynamic>? ?? <dynamic>[];
      return payments;
    }

    String msg = 'Failed to load payments: ${resp.statusCode}';
    try {
      final j = jsonDecode(resp.body);
      if (j is Map && j['detail'] != null) msg = j['detail'].toString();
    } catch (_) {}
    throw Exception('$msg ${resp.body}');
  }

  Future<File> downloadReceiptByTransactionId({
    required String token,
    required int transactionId,
    void Function(int, int)? onProgress,
    bool openAfterDownload = true,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    // Remove '/clients' from the URL
    final url = '$base/transaction/$transactionId/receipt/';

    final dir = await getTemporaryDirectory();
    final filePath = '${dir.path}/receipt_txn_$transactionId.pdf';
    final file = File(filePath);

    try {
      final resp = await _dio.get<List<int>>(
        url,
        options: Options(
          headers: {'Authorization': 'Token $token'},
          responseType: ResponseType.bytes,
          validateStatus: (s) => s != null && s < 500,
        ),
        onReceiveProgress: (rec, total) {
          if (onProgress != null) onProgress(rec, total);
        },
      ).timeout(timeout);

      final status = resp.statusCode ?? 0;
      if (status == 200 && resp.data != null && resp.data!.isNotEmpty) {
        await file.writeAsBytes(resp.data!, flush: true);
        if (openAfterDownload) await OpenFile.open(file.path);
        return file;
      } else if (status == 403) {
        throw Exception(
            'Forbidden: you are not allowed to access this receipt (403)');
      } else if (status == 404) {
        throw Exception('Receipt not found (404)');
      } else {
        final text = resp.data != null ? String.fromCharCodes(resp.data!) : '';
        throw Exception('Failed to download (status: $status) $text');
      }
    } on DioError catch (e) {
      throw Exception('Network/download error: ${e.message}');
    }
  }

  Future<File> _downloadSignedUrlToFile({
    required String signedUrl,
    required String fileName,
    void Function(int, int)? onProgress,
    bool openAfterDownload = true,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final dir = await getTemporaryDirectory();
    final filePath = '${dir.path}/$fileName';
    final file = File(filePath);

    try {
      final resp = await _dio.get<List<int>>(
        signedUrl,
        options: Options(
          responseType: ResponseType.bytes,
          validateStatus: (s) => s != null && s < 500,
        ),
        onReceiveProgress: (rec, total) {
          if (onProgress != null) onProgress(rec, total);
        },
      ).timeout(timeout);

      final status = resp.statusCode ?? 0;
      if (status == 200 && resp.data != null && resp.data!.isNotEmpty) {
        await file.writeAsBytes(resp.data!, flush: true);
        if (openAfterDownload) await OpenFile.open(file.path);
        return file;
      } else if (status == 404) {
        throw Exception('notfound');
      } else {
        final text = resp.data != null ? String.fromCharCodes(resp.data!) : '';
        throw Exception(
            'Failed to download signed url (status: $status) $text');
      }
    } on DioError catch (e) {
      throw Exception('Network/download error (signed url): ${e.message}');
    }
  }

  Future<File?> downloadReceiptWithFallback({
    required String token,
    String? reference,
    int? transactionId,
    void Function(int, int)? onProgress,
    bool openAfterDownload = true,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    if ((reference == null || reference.isEmpty) && transactionId == null) {
      throw Exception('Reference or transactionId required');
    }

    String? ref = reference;
    if ((ref == null || ref.isEmpty) && transactionId != null) {
      try {
        final tx = await getTransactionDetail(
            token: token, transactionId: transactionId);
        ref = (tx['reference_code'] ?? tx['receipt_number'] ?? tx['reference'])
            ?.toString();
      } catch (_) {
        ref = null;
      }
    }

    if (ref == null || ref.isEmpty) {
      if (transactionId != null) {
        return await downloadReceiptByTransactionId(
          token: token,
          transactionId: transactionId,
          onProgress: onProgress,
          openAfterDownload: openAfterDownload,
          timeout: timeout,
        );
      }
      throw Exception('No reference available to download receipt');
    }

    final safeRef = ref;
    final fileName = 'receipt_${Uri.encodeComponent(safeRef)}.pdf';

    // 1) Try direct token-authenticated download (fast, in-app)
    try {
      final file = await downloadReceiptByReference(
        token: token,
        reference: safeRef,
        onProgress: onProgress,
        openAfterDownload: openAfterDownload,
        timeout: timeout,
      );
      return file;
    } catch (e) {
      final s = e.toString().toLowerCase();
      // If error indicates auth problem or headers stripped, fallback to signed-url flow
      if (s.contains('auth:') ||
          s.contains('401') ||
          s.contains('403') ||
          s.contains('auth')) {
        // Request signed url from server
        String? signedUrl;
        try {
          signedUrl =
              await requestReceiptDownloadUrl(token: token, reference: safeRef);
        } catch (reqErr) {
          throw Exception('Failed to request signed download URL: $reqErr');
        }

        if (signedUrl == null || signedUrl.isEmpty) {
          throw Exception('Signed download URL not returned by server');
        }

        // Download the signed URL bytes inside the app (no auth header)
        final file = await _downloadSignedUrlToFile(
          signedUrl: signedUrl,
          fileName: fileName,
          onProgress: onProgress,
          openAfterDownload: openAfterDownload,
          timeout: timeout,
        );
        return file;
      }

      // If not an auth error, rethrow so caller can handle (maybe 'notfound', network issues, etc.)
      rethrow;
    }
  }

  Future<String?> requestReceiptDownloadUrl({
    required String token,
    required String reference,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/clients/receipts/request-download/');
    final resp = await http
        .post(uri,
            headers: {
              'Authorization': 'Token $token',
              'Accept': 'application/json',
              'Content-Type': 'application/json',
            },
            body: jsonEncode({'reference': reference}))
        .timeout(timeout);

    if (resp.statusCode == 200) {
      final data = jsonDecode(resp.body) as Map<String, dynamic>;
      return data['download_url'] as String?;
    }

    throw Exception(
        'Failed to request signed download URL: ${resp.statusCode} ${resp.body}');
  }

  Future<File> downloadReceiptByReference({
    required String token,
    required String reference,
    void Function(int, int)? onProgress,
    bool openAfterDownload = true,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final safeRef = Uri.encodeComponent(reference);
    final url = '$base/clients/receipts/download/?reference=$safeRef';

    final dir = await getTemporaryDirectory();
    final filePath = '${dir.path}/receipt_$safeRef.pdf';
    final file = File(filePath);

    try {
      final resp = await _dio.get<List<int>>(url,
          options: Options(
            headers: {'Authorization': 'Token $token'},
            responseType: ResponseType.bytes,
            validateStatus: (s) => s != null && s < 500,
          ), onReceiveProgress: (rec, total) {
        if (onProgress != null) onProgress(rec, total);
      }).timeout(timeout);

      final status = resp.statusCode ?? 0;
      if (status == 200 && resp.data != null && resp.data!.isNotEmpty) {
        await file.writeAsBytes(resp.data!, flush: true);
        if (openAfterDownload) await OpenFile.open(file.path);
        return file;
      } else if (status == 401 || status == 403) {
        throw Exception('auth:${status}');
      } else if (status == 404) {
        throw Exception('notfound');
      } else {
        final text = resp.data != null ? String.fromCharCodes(resp.data!) : '';
        throw Exception('Failed to download (status: $status) $text');
      }
    } on DioError catch (e) {
      throw Exception('Network/download error: ${e.message}');
    }
  }

  // =========================
  // =========================================================================
  // NOTIFICATIONS (CLIENT) - notification.html page
  // =========================================================================
  Future<Map<String, dynamic>> getClientNotificationPageData({
    required String token,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/api/client/notifications/';
    final headers = <String, String>{
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    try {
      final resp = await http
          .get(Uri.parse(url), headers: headers)
          .timeout(const Duration(seconds: 30));
      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Notification page data request timed out');
    }
  }

  /// Fetch notifications with pagination and filtering
  Future<Map<String, dynamic>> fetchClientNotifications({
    required String token,
    int page = 1,
    String filter = 'all',
    String? since,
    int pageSize = 12,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final params = <String, String>{
      'page': page.toString(),
      'filter': filter,
      'page_size': pageSize.toString(),
    };
    if (since != null && since.isNotEmpty) {
      params['since'] = since;
    }

    final uri = Uri.parse('$baseUrl/api/client/notifications/list/')
        .replace(queryParameters: params);

    final headers = <String, String>{
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    try {
      final resp = await http
          .get(uri, headers: headers)
          .timeout(const Duration(seconds: 30));
      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Notification list request timed out');
    }
  }

  /// Get details of a single notification
  /// GET /api/client/notifications/<id>/detail/
  Future<Map<String, dynamic>> getClientNotificationDetail({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/api/client/notifications/$userNotificationId/detail/';

    try {
      final resp = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json; charset=utf-8',
          'Accept': 'application/json; charset=utf-8',
          'Accept-Charset': 'utf-8',
        },
      ).timeout(const Duration(seconds: 20));

      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Notification detail request timed out');
    }
  }

  /// Get unread notification counts
  Future<Map<String, int>> getClientUnreadCounts(String token) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/api/client/notifications/unread-count/';

    try {
      final resp = await http.get(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 15));

      final parsed = await _handleResponse(resp);

      // Ensure ints
      final Map<String, dynamic> map = Map<String, dynamic>.from(parsed as Map);
      return {
        'unread': (map['unread_count'] is int)
            ? map['unread_count']
            : int.tryParse(map['unread_count']?.toString() ?? '0') ?? 0,
        'total': (map['total_count'] is int)
            ? map['total_count']
            : int.tryParse(map['total_count']?.toString() ?? '0') ?? 0,
      };
    } on TimeoutException {
      throw Exception('Unread count request timed out');
    }
  }

  /// Mark a notification as read
  Future<Map<String, dynamic>> markClientNotificationRead({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url =
        '$baseUrl/api/client/notifications/$userNotificationId/mark-read/';

    try {
      final resp = await http.post(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 20));

      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Mark read request timed out');
    }
  }

  /// Mark a notification as unread
  /// POST /api/client/notifications/<id>/mark-unread/
  Future<Map<String, dynamic>> markClientNotificationUnread({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url =
        '$baseUrl/api/client/notifications/$userNotificationId/mark-unread/';

    try {
      final resp = await http.post(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 20));

      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Mark unread request timed out');
    }
  }

  /// Mark all notifications as read
  /// POST /api/client/notifications/mark-all-read/
  Future<Map<String, int>> markClientAllNotificationsRead({
    required String token,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/api/client/notifications/mark-all-read/';

    try {
      final resp = await http.post(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 20));

      final parsed = await _handleResponse(resp);
      final map = Map<String, dynamic>.from(parsed as Map);

      return {
        'marked': (map['marked'] is int)
            ? map['marked']
            : int.tryParse(map['marked']?.toString() ?? '0') ?? 0,
      };
    } on TimeoutException {
      throw Exception('Mark all read request timed out');
    }
  }

  /// Helper: Fetch notifications since a specific datetime
  Future<Map<String, dynamic>> fetchClientNotificationsSince({
    required String token,
    required String sinceIso,
    int pageSize = 50,
  }) async {
    return await fetchClientNotifications(
      token: token,
      page: 1,
      filter: 'all',
      since: sinceIso,
      pageSize: pageSize,
    );
  }

  /// Delete a notification
  /// POST /api/client/notifications/<id>/delete/
  Future<Map<String, dynamic>> deleteClientNotification({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/api/client/notifications/$userNotificationId/delete/';

    try {
      final resp = await http.post(
        Uri.parse(url),
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
        },
      ).timeout(const Duration(seconds: 20));

      final parsed = await _handleResponse(resp);
      return Map<String, dynamic>.from(parsed as Map);
    } on TimeoutException {
      throw Exception('Delete notification request timed out');
    }
  }

  // =========================================================================
  // NOTIFICATIONS (MARKETER)
  // =========================

  Future<Map<String, dynamic>> fetchMarketerNotifications({
    required String token,
    int page = 1,
    String filter = 'all',
    String? since,
    int pageSize = 12,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final params = <String, String>{
      'page': page.toString(),
      'filter': filter,
      'page_size': pageSize.toString(),
    };
    if (since != null && since.isNotEmpty) {
      params['since'] = since;
    }

    final uri = Uri.parse('$baseUrl/marketers/notifications/')
        .replace(queryParameters: params);

    final headers = <String, String>{
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    final resp = await http.get(uri, headers: headers);
    final parsed = await _handleResponse(resp);
    return Map<String, dynamic>.from(parsed as Map);
  }

  /// Fetch the "page" shaped marketer notifications payload used by the
  /// server-rendered `marketer_side/notification.html` page. Returns a map
  /// with keys: `stats`, `unread_list`, `read_list`.
  ///
  /// This method is non‑breaking and intended for the notifications *page*
  /// UI; existing paginated APIs are preserved for infinite-scroll lists.
  Future<Map<String, dynamic>> fetchMarketerNotificationsPage({
    required String token,
  }) async {
    if (token.isEmpty) throw Exception('Authentication token is required');

    final uri = Uri.parse('$baseUrl/api/marketer/notifications/');
    final headers = {
      'Authorization': 'Token $token',
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };

    final resp = await http.get(uri, headers: headers);
    final parsed = await _handleResponse(resp);
    final Map<String, dynamic> payload =
        Map<String, dynamic>.from(parsed as Map);

    // Normalize any nested media/company logos so callers can render safely.
    try {
      final unread = payload['unread_list'] as List? ?? <dynamic>[];
      final read = payload['read_list'] as List? ?? <dynamic>[];
      for (final item in [...unread, ...read]) {
        if (item is Map<String, dynamic>) {
          _normalizeMediaUrls(item);
          final notif = item['notification'];
          if (notif is Map<String, dynamic>) _normalizeMediaUrls(notif);
        }
      }
    } catch (_) {
      // defensive: parsing/normalization should not break callers
    }

    return payload;
  }

  Future<Map<String, dynamic>> getMarketerNotificationDetail({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/marketers/notifications/$userNotificationId/';
    final resp = await http.get(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json; charset=utf-8',
        'Accept': 'application/json; charset=utf-8',
        'Accept-Charset': 'utf-8',
      },
    );
    final parsed = await _handleResponse(resp);
    return Map<String, dynamic>.from(parsed as Map);
  }

  /// Fetch the marketer notification *detail page* payload.
  /// Endpoint: GET /marketers/notifications/<id>/detail/?auto_read=true
  /// Returns a flattened UserNotification-like map (keys: id, notification, read, created_at)
  Future<Map<String, dynamic>> getMarketerNotificationDetailPage({
    required String token,
    required int userNotificationId,
    bool autoRead = true,
  }) async {
    if (token.isEmpty) throw Exception('Authentication token is required');

    final url =
        '$baseUrl/marketers/notifications/$userNotificationId/detail/?auto_read=${autoRead ? 'true' : 'false'}';
    final resp = await http.get(Uri.parse(url), headers: {
      'Authorization': 'Token $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    });

    final parsed = await _handleResponse(resp);
    final payload = Map<String, dynamic>.from(parsed as Map);

    // payload expected: { 'notification': <UserNotification>, 'is_read': bool }
    final userNotif = Map<String, dynamic>.from(payload['notification'] ?? {});

    // Ensure read flag reflects page 'is_read'
    if (payload.containsKey('is_read')) {
      userNotif['read'] = payload['is_read'] == true;
    }

    // Normalize nested media and company fields safely
    try {
      _normalizeMediaUrls(userNotif);
      final notif = userNotif['notification'];
      if (notif is Map<String, dynamic>) {
        _normalizeMediaUrls(notif);

        // Ensure company initial exists for avatar fallback
        final company = notif['company'] as Map<String, dynamic>?;
        if (company != null) {
          if (company['initial'] == null ||
              (company['initial'] is String &&
                  company['initial'].toString().isEmpty)) {
            final name = company['company_name'] ?? company['name'] ?? '';
            company['initial'] = (name is String && name.isNotEmpty)
                ? name[0].toUpperCase()
                : 'S';
          }
        }
      }
    } catch (_) {
      // defensive: normalization should not fail callers
    }

    return userNotif;
  }

  /// Delete a UserNotification for a marketer.
  /// DELETE /marketers/notifications/<id>/delete/
  Future<bool> deleteMarketerNotification({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) throw Exception('Authentication token is required');

    final url = '$baseUrl/marketers/notifications/$userNotificationId/delete/';
    final resp = await http.delete(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Accept': 'application/json',
      },
    );

    if (resp.statusCode == 200) return true;
    if (resp.statusCode == 401) throw Exception('Unauthorized');
    if (resp.statusCode == 404) throw Exception('Notification not found');

    // Fallback: attempt to parse response body for success
    final parsed = await _handleResponse(resp);
    if (parsed is Map<String, dynamic> && parsed.containsKey('id')) return true;

    return false;
  }

  Future<Map<String, int>> getMarketerUnreadCounts(String token) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/marketers/notifications/unread-count/';
    final resp = await http.get(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'User-Agent': 'RealEstateMSApp/1.0 (Android)',
        'X-Requested-With': 'XMLHttpRequest',
      },
    );

    final parsed = await _handleResponse(resp);
    final Map<String, dynamic> map = Map<String, dynamic>.from(parsed as Map);
    return {
      'unread': (map['unread'] is int)
          ? map['unread']
          : int.tryParse(map['unread']?.toString() ?? '0') ?? 0,
      'total': (map['total'] is int)
          ? map['total']
          : int.tryParse(map['total']?.toString() ?? '0') ?? 0,
    };
  }

  Future<Map<String, dynamic>> markMarketerNotificationRead({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url =
        '$baseUrl/marketers/notifications/$userNotificationId/mark-read/';
    final resp = await http.post(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    final parsed = await _handleResponse(resp);
    return Map<String, dynamic>.from(parsed as Map);
  }

  Future<Map<String, dynamic>> markMarketerNotificationUnread({
    required String token,
    required int userNotificationId,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url =
        '$baseUrl/marketers/notifications/$userNotificationId/mark-unread/';
    final resp = await http.post(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    final parsed = await _handleResponse(resp);
    return Map<String, dynamic>.from(parsed as Map);
  }

  Future<Map<String, int>> markMarketerAllNotificationsRead({
    required String token,
  }) async {
    if (token.isEmpty) {
      throw Exception('Authentication token is required');
    }

    final url = '$baseUrl/marketers/notifications/mark-all-read/';
    final resp = await http.post(
      Uri.parse(url),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );
    final parsed = await _handleResponse(resp);
    final map = Map<String, dynamic>.from(parsed as Map);
    return {
      'marked': (map['marked'] is int)
          ? map['marked']
          : int.tryParse(map['marked']?.toString() ?? '0') ?? 0,
    };
  }

  // MARKETER SIDE

  // marketer dashboard
  Future<Map<String, dynamic>> fetchMarketerDashboard({
    required String token,
    int? marketerId,
  }) async {
    // Primary (canonical) endpoint
    final buffer = StringBuffer('$baseUrl/marketers/dashboard/');
    if (marketerId != null) {
      buffer
          .write('?marketer_id=${Uri.encodeComponent(marketerId.toString())}');
    }

    final response = await http.get(
      Uri.parse(buffer.toString()),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    // If the canonical endpoint returns a payload, normalize it and return a
    // predictable shape. If the canonical endpoint is missing expected keys
    // we'll attempt a safe fallback to the profile endpoint which exposes
    // `dashboard_summary` (server-side compatibility surface).
    if (response.statusCode == 200) {
      final Map<String, dynamic> raw =
          jsonDecode(response.body) as Map<String, dynamic>;

      // If the server returned a profile-like payload that contains the
      // canonical dashboard under `dashboard_summary`, prefer that.
      final Map<String, dynamic> payload =
          (raw['dashboard_summary'] is Map<String, dynamic>)
              ? Map<String, dynamic>.from(raw['dashboard_summary'] as Map)
              : Map<String, dynamic>.from(raw);

      // Ensure blocks and companies are present (apply safe fallbacks)
      final out = <String, dynamic>{};

      // summary / dashboard_summary (keep both keys for consumers)
      if (payload['summary'] is Map) {
        out['dashboard_summary'] =
            Map<String, dynamic>.from(payload['summary']);
      } else if (payload['dashboard_summary'] is Map) {
        out['dashboard_summary'] =
            Map<String, dynamic>.from(payload['dashboard_summary']);
      } else if (raw['dashboard_summary'] is Map) {
        out['dashboard_summary'] =
            Map<String, dynamic>.from(raw['dashboard_summary']);
      } else {
        // try older top-level fields
        out['dashboard_summary'] = {
          'total_transactions': _asInt(payload['total_transactions'] ??
              payload['total_tx'] ??
              payload['tx_count']),
          'number_clients':
              _asInt(payload['number_clients'] ?? payload['clients_count']),
          'total_companies': _asInt(payload['total_companies'] ??
              payload['companies_count'] ??
              payload['total_estates_sold']),
        };
      }

      // Blocks: weekly/monthly/yearly/alltime — accept canonical and legacy shapes
      for (final k in ['weekly', 'monthly', 'yearly', 'alltime']) {
        final Map<String, dynamic>? b = _extractDashboardBlock(payload, k) ??
            _extractDashboardBlock(raw, k);
        if (b != null) out[k] = b;
      }

      // Companies list (canonical) with legacy-array fallback
      out['companies'] = _parseCompanies(payload) ??
          _parseCompanies(raw) ??
          <Map<String, dynamic>>[];

      // Preserve legacy arrays if present (back-compat)
      if (payload['company_names'] != null)
        out['company_names'] = payload['company_names'];
      if (payload['company_transactions'] != null)
        out['company_transactions'] = payload['company_transactions'];

      // Keep the original raw payload accessible (useful for incremental rollouts)
      out['_raw'] = raw;

      return out;
    }

    // If canonical endpoint failed, attempt profile endpoint as a guarded fallback
    // (profile endpoint exposes `dashboard_summary` in some deployments).
    try {
      final profile = await getMarketerProfileByToken(token: token);
      if (profile['dashboard_summary'] is Map<String, dynamic>) {
        final Map<String, dynamic> ds =
            Map<String, dynamic>.from(profile['dashboard_summary'] as Map);
        final out = <String, dynamic>{
          'dashboard_summary': ds,
          'companies': _parseCompanies(ds) ?? <Map<String, dynamic>>[],
          '_raw_profile': profile,
        };

        // copy blocks if present
        for (final k in ['weekly', 'monthly', 'yearly', 'alltime']) {
          final b = _extractDashboardBlock(ds, k);
          if (b != null) out[k] = b;
        }
        return out;
      }
    } catch (_) {
      // fall through to surface the original error below
    }

    throw Exception(
        'Failed to fetch marketer dashboard: ${response.statusCode} - ${response.body}');
  }

  Future<Map<String, dynamic>> fetchMarketerChartRange({
    required String token,
    String range = 'weekly',
    int? marketerId,
  }) async {
    // Only accept supported ranges; default to weekly
    const supported = {'weekly', 'monthly', 'yearly', 'alltime'};
    final r = supported.contains(range) ? range : 'weekly';

    // Preferred (canonical) path: fetch the full dashboard which now contains
    // `weekly` / `monthly` / `yearly` / `alltime` blocks. This keeps the
    // client aligned with the server-side consolidation.
    try {
      final dashboard = await fetchMarketerDashboard(
        token: token,
        marketerId: marketerId,
      );

      final dynamic candidate = dashboard[r];
      if (candidate is Map<String, dynamic>) return Map.from(candidate);

      // Back-compat: some payloads may nest the block under `data` / `chart`
      if (dashboard['data'] is Map && dashboard['data'][r] is Map) {
        return Map<String, dynamic>.from(dashboard['data'][r] as Map);
      }
      if (candidate is List && candidate.isNotEmpty && candidate.first is Map) {
        return Map<String, dynamic>.from(candidate.first as Map);
      }
      // If canonical response didn't include the range block, fall through to
      // the legacy endpoint below as a safe fallback.
    } catch (_) {
      // Intentionally swallow — we'll attempt the legacy endpoint next.
    }

    // Legacy fallback (kept for transition). If the server still supports the
    // old `dashboard/data` endpoint we'll use it; otherwise this will surface
    // a clear error to the caller.
    final params = StringBuffer('?range=${Uri.encodeQueryComponent(r)}');
    if (marketerId != null) {
      params
          .write('&marketer_id=${Uri.encodeComponent(marketerId.toString())}');
    }

    final response = await http.get(
      Uri.parse('$baseUrl/marketers/dashboard/data/$params'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final decoded = jsonDecode(response.body);
      if (decoded is Map<String, dynamic>) return decoded;
      if (decoded is List && decoded.isNotEmpty && decoded.first is Map) {
        return Map<String, dynamic>.from(decoded.first as Map);
      }
    }

    throw Exception(
        'Failed to fetch marketer chart range (canonical and fallback): ${response.statusCode} - ${response.body}');
  }

  List<Map<String, dynamic>> parseChartBlockToChartData(
      Map<String, dynamic> block) {
    final List<dynamic> labels = (block['labels'] ?? []) as List<dynamic>;
    final List<dynamic> tx = (block['tx'] ?? []) as List<dynamic>;
    // prefer canonical `comp` (company-scoped transactions); fall back to `est`
    final List<dynamic> comp =
        (block['comp'] ?? block['est'] ?? []) as List<dynamic>;
    final List<dynamic> cli = (block['cli'] ?? []) as List<dynamic>;

    final int n = labels.length;
    final List<Map<String, dynamic>> out = List.empty(growable: true);

    for (var i = 0; i < n; i++) {
      final String time = labels[i]?.toString() ?? '';
      final double sales = _toDoubleSafe(i < tx.length ? tx[i] : 0);
      final double companyMetric = _toDoubleSafe(i < comp.length ? comp[i] : 0);
      final double customers = _toDoubleSafe(i < cli.length ? cli[i] : 0);

      out.add({
        'time': time,
        'sales': sales,
        // new canonical field (preferred by server)
        'company_metric': companyMetric,
        // keep `revenue` for backward-compatibility (maps to company_metric)
        'revenue': companyMetric,
        'customers': customers,
      });
    }
    return out;
  }

  // Helper: safely parse int-like values returned by the API (string/num/null)
  int _asInt(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String) return int.tryParse(v.replaceAll(',', '')) ?? 0;
    return 0;
  }

  Map<String, dynamic>? _extractDashboardBlock(
      Map<String, dynamic> payload, String key) {
    // Accept canonical top-level block
    final candidate = payload[key];
    if (candidate is Map<String, dynamic>)
      return Map<String, dynamic>.from(candidate);

    // Accept list-wrapped blocks
    if (candidate is List && candidate.isNotEmpty && candidate.first is Map) {
      return Map<String, dynamic>.from(candidate.first as Map);
    }

    // Common legacy nesting locations
    if (payload['data'] is Map && payload['data'][key] is Map) {
      return Map<String, dynamic>.from(payload['data'][key] as Map);
    }
    if (payload['chart'] is Map && payload['chart'][key] is Map) {
      return Map<String, dynamic>.from(payload['chart'][key] as Map);
    }
    if (payload['blocks'] is Map && payload['blocks'][key] is Map) {
      return Map<String, dynamic>.from(payload['blocks'][key] as Map);
    }

    // Profile-shaped payload: dashboard_summary: { weekly: {...} }
    if (payload['dashboard_summary'] is Map &&
        payload['dashboard_summary'][key] is Map) {
      return Map<String, dynamic>.from(
          payload['dashboard_summary'][key] as Map);
    }

    return null;
  }

  /// Normalizes `companies[]` or legacy `company_names`/`company_transactions`
  List<Map<String, dynamic>>? _parseCompanies(Map<String, dynamic>? payload) {
    if (payload == null) return null;

    // Canonical list
    if (payload['companies'] is List) {
      final raw = payload['companies'] as List;
      return raw
          .map((e) {
            if (e is Map<String, dynamic>) {
              return {
                'company_id': e['company_id'] ?? e['id'] ?? null,
                'company_name': e['company_name'] ?? e['name'] ?? '',
                'transactions':
                    _asInt(e['transactions'] ?? e['tx'] ?? e['count']),
                'company_logo': e['company_logo'] ?? e['logo'] ?? null,
              };
            }
            return null;
          })
          .whereType<Map<String, dynamic>>()
          .toList();
    }

    // Legacy parallel arrays: company_names[] and company_transactions[]
    if (payload['company_names'] is List &&
        payload['company_transactions'] is List) {
      final List names = payload['company_names'] as List;
      final List txs = payload['company_transactions'] as List;
      final n = names.length < txs.length ? names.length : txs.length;
      final out = <Map<String, dynamic>>[];
      for (var i = 0; i < n; i++) {
        out.add({
          'company_id': null,
          'company_name': names[i]?.toString() ?? '',
          'transactions': _asInt(txs[i]),
          'company_logo': null,
        });
      }
      return out;
    }

    return null;
  }

  /// Fetch the marketer-side "My Companies" page payload.
  /// Endpoint: GET /api/marketer/my-companies/
  /// Returns a map with keys: `companies` (List<Map>) and `current_year` (int).
  Future<Map<String, dynamic>> getMarketerMyCompanies({
    required String token,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/api/marketer/my-companies/');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token.isNotEmpty) headers['Authorization'] = 'Token $token';

    final resp = await http.get(uri, headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      if (decoded is Map<String, dynamic> &&
          decoded['success'] == true &&
          decoded['data'] is Map) {
        final Map<String, dynamic> data =
            Map<String, dynamic>.from(decoded['data']);
        final rawCompanies = (data['companies'] as List?) ?? <dynamic>[];
        final companies = rawCompanies.map<Map<String, dynamic>>((c) {
          final Map<String, dynamic> item = Map<String, dynamic>.from(c as Map);
          final Map<String, dynamic> company =
              Map<String, dynamic>.from(item['company'] ?? {});
          company['logo_url'] = _absUrl(company['logo_url']);
          // preserve initial and location if provided by the API
          if (company['initial'] != null)
            company['initial'] = company['initial']?.toString();
          if (company['location'] != null)
            company['location'] = company['location']?.toString();
          item['company'] = company;

          // normalize numeric fields for safe UI usage
          item['closed_deals'] = (item['closed_deals'] is int)
              ? item['closed_deals']
              : int.tryParse(item['closed_deals']?.toString() ?? '') ?? 0;
          item['client_count'] = (item['client_count'] is int)
              ? item['client_count']
              : int.tryParse(item['client_count']?.toString() ?? '') ?? 0;
          item['monthly_sales'] = _toDoubleSafe(item['monthly_sales']);
          item['quarterly_sales'] = _toDoubleSafe(item['quarterly_sales']);
          item['total_year_sales'] = _toDoubleSafe(item['total_year_sales']);
          item['commission_rate'] = _toDoubleSafe(item['commission_rate']);

          // normalize achievement percentages (may be null)
          item['yearly_target_achievement'] =
              item['yearly_target_achievement'] != null
                  ? _toDoubleSafe(item['yearly_target_achievement'])
                  : null;
          item['monthly_achievement'] = item['monthly_achievement'] != null
              ? _toDoubleSafe(item['monthly_achievement'])
              : null;
          item['quarterly_achievement'] = item['quarterly_achievement'] != null
              ? _toDoubleSafe(item['quarterly_achievement'])
              : null;

          // normalize boolean-ish has_transactions
          final ht = item['has_transactions'];
          if (ht is bool) {
            item['has_transactions'] = ht;
          } else if (ht is int) {
            item['has_transactions'] = ht != 0;
          } else if (ht is String) {
            item['has_transactions'] = ht.toLowerCase() == 'true';
          } else {
            item['has_transactions'] = false;
          }

          // ranks: keep null when absent, otherwise coerce to int
          item['rank_position'] =
              item.containsKey('rank_position') && item['rank_position'] != null
                  ? _asInt(item['rank_position'])
                  : null;
          item['rank_total'] =
              item.containsKey('rank_total') && item['rank_total'] != null
                  ? _asInt(item['rank_total'])
                  : null;
          item['rank_label'] =
              item['rank_label'] != null ? item['rank_label'].toString() : null;

          // normalize nested target amounts if present
          if (item['monthly_target'] is Map &&
              item['monthly_target']['target_amount'] != null) {
            item['monthly_target']['target_amount'] =
                _toDoubleSafe(item['monthly_target']['target_amount']);
          }
          if (item['quarterly_target'] is Map &&
              item['quarterly_target']['target_amount'] != null) {
            item['quarterly_target']['target_amount'] =
                _toDoubleSafe(item['quarterly_target']['target_amount']);
          }
          if (item['yearly_target'] is Map &&
              item['yearly_target']['target_amount'] != null) {
            item['yearly_target']['target_amount'] =
                _toDoubleSafe(item['yearly_target']['target_amount']);
          }

          return item;
        }).toList();
        return {
          'companies': companies,
          'current_year': _asInt(data['current_year'])
        };
      }
      throw Exception((decoded as Map)['message'] ??
          'Unexpected response for marketer companies');
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication required');
    } else {
      String msg = 'Failed to fetch marketer companies (${resp.statusCode})';
      try {
        final decoded = jsonDecode(resp.body);
        if (decoded is Map && decoded['message'] != null)
          msg = decoded['message'];
      } catch (_) {}
      throw Exception(msg);
    }
  }

  /// Fetch marketer's portfolio for a specific company.
  /// Endpoint: GET /api/marketer/company/{company_id}/portfolio/
  /// Returns: { company_id, company_name, total_value, transactions: [...], clients: [...] }
  Future<Map<String, dynamic>> getMarketerCompanyPortfolio({
    required int companyId,
    required String token,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri =
        Uri.parse('$baseUrl/api/marketer/company/$companyId/portfolio/');
    final headers = <String, String>{'Content-Type': 'application/json'};
    if (token.isNotEmpty) headers['Authorization'] = 'Token $token';

    final resp = await http.get(uri, headers: headers).timeout(timeout);
    if (resp.statusCode == 200) {
      final decoded = jsonDecode(resp.body);
      if (decoded is Map<String, dynamic> &&
          decoded['success'] == true &&
          decoded['data'] is Map) {
        final Map<String, dynamic> data =
            Map<String, dynamic>.from(decoded['data']);
        final txs = ((data['transactions'] as List?) ?? [])
            .map<Map<String, dynamic>>((tx) {
          final Map<String, dynamic> m = Map<String, dynamic>.from(tx as Map);
          m['amount'] = _toDoubleSafe(m['amount']);
          // normalize allocation nested fields if present
          if (m['allocation'] is Map) {
            final alloc = Map<String, dynamic>.from(m['allocation'] as Map);
            if (alloc['plot_size'] != null)
              alloc['plot_size'] = alloc['plot_size'];
            if (alloc['estate'] is Map && alloc['estate']['name'] != null) {
              alloc['estate']['name'] = alloc['estate']['name'];
            }
            m['allocation'] = alloc;
          }
          return m;
        }).toList();
        data['transactions'] = txs;

        final clients =
            ((data['clients'] as List?) ?? []).map<Map<String, dynamic>>((c) {
          final Map<String, dynamic> m = Map<String, dynamic>.from(c as Map);
          // normalize profile image url
          if (m['profile_image'] is String)
            m['profile_image'] = _absUrl(m['profile_image']);

          // normalize company_transactions
          if (m['company_transactions'] is List) {
            m['company_transactions'] = (m['company_transactions'] as List)
                .map<Map<String, dynamic>>((tx) {
              final Map<String, dynamic> t =
                  Map<String, dynamic>.from(tx as Map);
              t['amount'] = _toDoubleSafe(t['amount']);
              if (t['allocation'] is Map) {
                final alloc = Map<String, dynamic>.from(t['allocation'] as Map);
                if (alloc['plot_size'] != null)
                  alloc['plot_size'] = alloc['plot_size'];
                if (alloc['estate'] is Map && alloc['estate']['name'] != null) {
                  alloc['estate']['name'] = alloc['estate']['name'];
                }
                t['allocation'] = alloc;
              }
              return t;
            }).toList();
          }

          return m;
        }).toList();
        data['clients'] = clients;

        // normalize top-level fields
        data['company_logo'] = _absUrl(data['company_logo']);
        data['total_value'] = _toDoubleSafe(data['total_value']);
        data['commission_earned'] = _toDoubleSafe(data['commission_earned']);
        data['commission_rate'] = _toDoubleSafe(data['commission_rate']);
        data['closed_deals'] = (data['closed_deals'] is int)
            ? data['closed_deals']
            : int.tryParse(data['closed_deals']?.toString() ?? '') ?? 0;

        // normalize leaderboard (top3) and the current user's entry (user_entry)
        // ensure ranks are ints and profile images are absolute URLs
        if (data['top3'] is List) {
          data['top3'] = (data['top3'] as List).map<Map<String, dynamic>>((e) {
            final Map<String, dynamic> entry =
                Map<String, dynamic>.from(e as Map);
            entry['rank'] = _asInt(entry['rank']);
            if (entry['marketer'] is Map) {
              final m = Map<String, dynamic>.from(entry['marketer'] as Map);
              m['id'] = _asInt(m['id']);
              if (m['profile_image'] is String)
                m['profile_image'] = _absUrl(m['profile_image']);
              entry['marketer'] = m;
            }
            return entry;
          }).toList();
        }

        if (data['user_entry'] is Map) {
          final Map<String, dynamic> ue =
              Map<String, dynamic>.from(data['user_entry'] as Map);
          ue['rank'] = _asInt(ue['rank']);
          if (ue['marketer'] is Map) {
            final m = Map<String, dynamic>.from(ue['marketer'] as Map);
            m['id'] = _asInt(m['id']);
            if (m['profile_image'] is String)
              m['profile_image'] = _absUrl(m['profile_image']);
            ue['marketer'] = m;
          }
          data['user_entry'] = ue;
        }

        // ensure current_year is an int when present
        if (data['current_year'] != null)
          data['current_year'] = _asInt(data['current_year']);

        return data;
      }
      throw Exception((decoded as Map)['message'] ??
          'Unexpected response for company portfolio');
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication required');
    } else if (resp.statusCode == 403) {
      throw Exception('Access denied to this company portfolio');
    } else if (resp.statusCode == 404) {
      throw Exception('Company portfolio not found');
    } else {
      throw Exception('Failed to fetch company portfolio: ${resp.statusCode}');
    }
  }

  double _toDoubleSafe(dynamic v) {
    if (v == null) return 0.0;
    if (v is int) return v.toDouble();
    if (v is double) return v;
    if (v is String) {
      final cleaned = v.replaceAll(',', '');
      return double.tryParse(cleaned) ?? 0.0;
    }
    if (v is num) return v.toDouble();
    return 0.0;
  }

  // marketer client's page
  Future<Map<String, dynamic>> fetchMarketerClients({
    required String token,
    int? marketerId,
    int page = 1,
    int pageSize = 12,
    String? search,
    bool? allocated,
  }) async {
    final queryParams = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    if (marketerId != null) queryParams['marketer_id'] = marketerId.toString();
    if (search != null && search.isNotEmpty) queryParams['search'] = search;
    if (allocated != null)
      queryParams['allocated'] = allocated ? 'true' : 'false';

    final uri = Uri.parse('$baseUrl/marketers/clients/')
        .replace(queryParameters: queryParams);
    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      // DRF paginated response
      final Map<String, dynamic> data = jsonDecode(response.body);
      // Normalize profile_image urls if present
      if (data['results'] is List) {
        for (final item in data['results']) {
          if (item is Map &&
              item['profile_image'] != null &&
              item['profile_image'] is String) {
            final img = item['profile_image'] as String;
            if (img.isNotEmpty && !img.startsWith('http')) {
              item['profile_image'] = '$baseUrl$img';
            }
          }
        }
      }
      return data;
    } else {
      throw Exception(
          'Failed to load clients: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> getMarketerClientDetail({
    required int clientId,
    required String token,
    int? marketerId,
  }) async {
    final query = marketerId != null ? '?marketer_id=$marketerId' : '';
    final uri = Uri.parse('$baseUrl/marketers/clients/$clientId/$query');
    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(response.body);

      // Normalize profile_image url
      if (data['profile_image'] != null && data['profile_image'] is String) {
        final img = data['profile_image'] as String;
        if (img.isNotEmpty && !img.startsWith('http')) {
          data['profile_image'] = '$baseUrl$img';
        }
      }

      // Optionally normalize nested transaction images/urls if any
      if (data['transactions_by_estate'] is List) {
        for (final estateGroup in data['transactions_by_estate']) {
          if (estateGroup is Map && estateGroup['transactions'] is List) {
            for (final txn in estateGroup['transactions']) {
              if (txn is Map && txn['plot_number'] == null) {
                // nothing to do, placeholder if you want to adapt later
              }
            }
          }
        }
      }

      return data;
    } else if (response.statusCode == 404) {
      throw Exception('Client not found (404)');
    } else if (response.statusCode == 403) {
      throw Exception('Permission denied (403)');
    } else {
      throw Exception(
          'Failed to fetch client detail: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> fetchClientTransactions({
    required int clientId,
    required String token,
    int page = 1,
    int pageSize = 12,
    int? estateId,
    bool? allocated,
    String? status,
    String? startDate,
    String? endDate,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };
    if (estateId != null) params['estate_id'] = estateId.toString();
    if (allocated != null) params['allocated'] = allocated ? 'true' : 'false';
    if (status != null && status.isNotEmpty) params['status'] = status;
    if (startDate != null && startDate.isNotEmpty)
      params['start_date'] = startDate;
    if (endDate != null && endDate.isNotEmpty) params['end_date'] = endDate;

    final uri = Uri.parse('$baseUrl/marketers/clients/$clientId/transactions/')
        .replace(queryParameters: params);
    final response = await http.get(
      uri,
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
    );

    if (response.statusCode == 200) {
      final Map<String, dynamic> data = jsonDecode(response.body);

      // Optionally adjust amounts / dates formatting client-side if needed
      return data;
    } else {
      throw Exception(
          'Failed to load transactions: ${response.statusCode} - ${response.body}');
    }
  }

  Future<Map<String, dynamic>> searchMarketerClients({
    required String token,
    String query = '',
    int page = 1,
    int pageSize = 12,
    int? marketerId,
  }) async {
    return await fetchMarketerClients(
      token: token,
      marketerId: marketerId,
      page: page,
      pageSize: pageSize,
      search: query,
    );
  }

  String buildWhatsAppLink(String rawPhone) {
    if (rawPhone == null) return '';
    String s = rawPhone.replaceAll(RegExp(r'[^\d+]'), '');
    s = s.replaceFirst(RegExp(r'^\+'), '');
    return 'https://wa.me/$s';
  }

  // Profile Methods
  Future<Map<String, dynamic>> getMarketerProfileByToken(
      {required String token}) async {
    final response = await http.get(
      Uri.parse('$baseUrl/marketers/profile/'),
      headers: {
        'Authorization': 'Token $token',
        'Accept': 'application/json',
        'User-Agent': 'RealEstateMSApp/1.0 (Android)',
        'X-Requested-With': 'XMLHttpRequest',
      },
    );

    final parsed = await _handleResponse(response);
    if (parsed is Map<String, dynamic>) return parsed;
    throw ApiException(
      message: 'Unexpected marketer profile response',
      details: 'Expected JSON object but received: ${parsed.runtimeType}',
      statusCode: response.statusCode,
    );
  }

  Future<Map<String, dynamic>> updateMarketerProfileDetails({
    required String token,
    String? about,
    String? company,
    String? job,
    String? country,
    File? profileImage,
  }) async {
    var request = http.MultipartRequest(
      'POST',
      Uri.parse('$baseUrl/marketers/profile/update/'),
    );

    request.headers['Authorization'] = 'Token $token';

    if (about != null) request.fields['about'] = about;
    if (company != null) request.fields['company'] = company;
    if (job != null) request.fields['job'] = job;
    if (country != null) request.fields['country'] = country;

    if (profileImage != null) {
      request.files.add(await http.MultipartFile.fromPath(
        'profile_image',
        profileImage.path,
      ));
    }

    final response = await request.send();
    final responseData = await response.stream.bytesToString();

    if (response.statusCode == 200) {
      return json.decode(responseData);
    } else {
      throw Exception('Failed to update marketer profile');
    }
  }

  Future<void> changeMarketerPassword({
    required String token,
    required String currentPassword,
    required String newPassword,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/marketers/change-password/'),
      headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
      },
      body: json.encode({
        'current_password': currentPassword,
        'new_password': newPassword,
      }),
    );

    if (response.statusCode != 200) {
      throw Exception('Failed to change password');
    }
  }

  // -------- HEADER API METHODS ----------------

  Map<String, String> _authHeaders(String? token,
      {String contentType = 'application/json'}) {
    if (token == null || token.trim().isEmpty) {
      throw Exception('No auth token provided to ApiService._authHeaders()');
    }
    return {
      'Content-Type': contentType,
      // DRF TokenAuthentication expects "Token <token>"
      'Authorization': 'Token ${token.trim()}',
      'User-Agent': 'RealEstateMSApp/1.0 (Android)',
      'X-Requested-With': 'XMLHttpRequest',
    };
  }

  String? _absUrl(String? path) {
    if (path == null) return null;
    final trimmed = path.trim();
    if (trimmed.isEmpty) return null;
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      return trimmed;
    }
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    if (!trimmed.startsWith('/')) {
      return '$base/$trimmed';
    }
    return '$base$trimmed';
  }

  // SHARED HEADER
  Future<Map<String, dynamic>> getHeaderDataShared({
    required String token,
  }) async {
    final headers = _authHeaders(token);
    final url = '$baseUrl/header-data/'; // DRF: /api/header-data/

    try {
      final resp = await http.get(Uri.parse(url), headers: headers);

      if (resp.statusCode == 200) {
        // Check if response is HTML error page (server error)
        if (resp.body.trim().startsWith('<!DOCTYPE') ||
            resp.body.trim().startsWith('<html')) {
          if (kDebugMode) {}
          // Return empty data to prevent infinite loop
          return {
            'total_unread': 0,
            'total_unread_count': 0,
            'global_message_count': 0,
            'unread_admin_count': 0,
          };
        }

        final Map<String, dynamic> data =
            jsonDecode(resp.body) as Map<String, dynamic>;

        // Normalize user.profile_image to absolute
        if (data.containsKey('user') && data['user'] is Map) {
          final user = Map<String, dynamic>.from(data['user'] as Map);
          if (user['profile_image'] != null) {
            user['profile_image'] = _absUrl(user['profile_image']?.toString());
          }
          data['user'] = user;
        }

        // Normalize unread_clients profile_image
        if (data['unread_clients'] is List) {
          final List clients = data['unread_clients'] as List;
          data['unread_clients'] = clients.map<Map<String, dynamic>>((c) {
            final m = Map<String, dynamic>.from(c as Map);
            if (m['profile_image'] != null) {
              m['profile_image'] = _absUrl(m['profile_image']?.toString());
            }
            return m;
          }).toList();
        }

        // Normalize unread_marketers profile_image (if admin)
        if (data['unread_marketers'] is List) {
          final List marketers = data['unread_marketers'] as List;
          data['unread_marketers'] = marketers.map<Map<String, dynamic>>((m) {
            final copy = Map<String, dynamic>.from(m as Map);
            if (copy['profile_image'] != null) {
              copy['profile_image'] =
                  _absUrl(copy['profile_image']?.toString());
            }
            return copy;
          }).toList();
        }

        // Notifications payload is already light; keep as-is
        if (data['unread_notifications'] is List) {
          data['unread_notifications'] = (data['unread_notifications'] as List)
              .map<Map<String, dynamic>>((e) => Map<String, dynamic>.from(
                  e is Map<String, dynamic> ? e : <String, dynamic>{}))
              .toList();
        }

        return data;
      } else if (resp.statusCode == 204) {
        // unauthenticated/no data
        return {
          'total_unread': 0,
          'total_unread_count': 0,
          'global_message_count': 0,
          'unread_admin_count': 0,
        };
      } else if (resp.statusCode == 401) {
        throw Exception('Authentication failed (401): ${resp.body}');
      } else if (resp.statusCode == 500) {
        if (kDebugMode) {}
        // Return empty data instead of throwing to prevent retry loop
        return {
          'total_unread': 0,
          'total_unread_count': 0,
          'global_message_count': 0,
          'unread_admin_count': 0,
        };
      } else {
        throw Exception(
            'Failed to fetch header data: ${resp.statusCode} ${resp.body}');
      }
    } on FormatException catch (e) {
      if (kDebugMode) {}
      // Return empty data on JSON parse failure
      return {
        'total_unread': 0,
        'total_unread_count': 0,
        'global_message_count': 0,
        'unread_admin_count': 0,
      };
    } catch (e) {
      if (kDebugMode) {}
      rethrow;
    }
  }

  Future<Map<String, dynamic>> getChatUnreadCountShared({
    required String token,
  }) async {
    final headers = _authHeaders(token);
    final url =
        '$baseUrl/client/chat/unread-count/'; // DRF: /api/client/chat/unread-count/

    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> data =
          jsonDecode(resp.body) as Map<String, dynamic>;
      // Map the DRF response to expected format
      final int unreadCount = data['unread_count'] ?? 0;
      return {
        'total_unread': unreadCount,
        'total_unread_count': unreadCount,
        'global_message_count':
            unreadCount, // For clients, this is messages from admin
        'unread_admin_count': unreadCount,
        'unread_count': unreadCount,
      };
    } else if (resp.statusCode == 204) {
      return {
        'total_unread': 0,
        'total_unread_count': 0,
        'global_message_count': 0,
        'unread_admin_count': 0,
      };
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication failed (401): ${resp.body}');
    } else {
      throw Exception(
          'Failed to fetch chat unread count: ${resp.statusCode} ${resp.body}');
    }
  }

  Future<List<Map<String, dynamic>>> getHeaderNotifications({
    required String token,
  }) async {
    final headers = _authHeaders(token);
    final url = '$baseUrl/notifications/'; // DRF: /api/notifications/

    try {
      final resp = await http.get(Uri.parse(url), headers: headers);

      if (resp.statusCode == 200) {
        // Check if response is HTML error page (server error)
        if (resp.body.trim().startsWith('<!DOCTYPE') ||
            resp.body.trim().startsWith('<html')) {
          if (kDebugMode) {}
          // Return empty list to prevent infinite loop
          return <Map<String, dynamic>>[];
        }

        final List<dynamic> data = jsonDecode(resp.body) as List<dynamic>;
        return data.map<Map<String, dynamic>>((e) {
          if (e is Map<String, dynamic>) return Map<String, dynamic>.from(e);
          return <String, dynamic>{};
        }).toList();
      } else if (resp.statusCode == 401) {
        throw Exception('Authentication failed (401): ${resp.body}');
      } else if (resp.statusCode == 500) {
        if (kDebugMode) {}
        // Return empty list instead of throwing to prevent retry loop
        return <Map<String, dynamic>>[];
      } else {
        throw Exception(
            'Failed to load notifications: ${resp.statusCode} ${resp.body}');
      }
    } on FormatException catch (e) {
      if (kDebugMode) {}
      // Return empty list on JSON parse failure
      return <Map<String, dynamic>>[];
    } catch (e) {
      if (kDebugMode) {}
      rethrow;
    }
  }

  Future<bool> markHeaderNotificationRead({
    required String token,
    required int userNotificationId,
  }) async {
    final headers = _authHeaders(token);
    final url =
        '$baseUrl/notifications/mark-read/$userNotificationId/'; // DRF: /api/notifications/mark-read/<pk>/

    final resp = await http.post(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      return true;
    } else if (resp.statusCode == 404) {
      return false;
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication failed (401): ${resp.body}');
    } else {
      throw Exception('Failed to mark read: ${resp.statusCode} ${resp.body}');
    }
  }

  Future<List<Map<String, dynamic>>> fetchAdminClientsWithUnreadShared({
    required String token,
  }) async {
    final headers = _authHeaders(token);
    final url =
        '$baseUrl/admin/clients/unread/'; // DRF: /api/admin/clients/unread/

    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> result =
          jsonDecode(resp.body) as Map<String, dynamic>;
      final clients = <Map<String, dynamic>>[];
      if (result['clients'] is List) {
        for (final item in (result['clients'] as List)) {
          if (item is Map<String, dynamic>) {
            if (item['profile_image'] != null) {
              item['profile_image'] =
                  _absUrl(item['profile_image']?.toString());
            }
            clients.add(Map<String, dynamic>.from(item));
          }
        }
      }
      return clients;
    } else if (resp.statusCode == 403) {
      throw Exception('Forbidden: admin-only endpoint.');
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication failed (401): ${resp.body}');
    } else {
      throw Exception(
          'Failed to fetch admin client chat list: ${resp.statusCode} ${resp.body}');
    }
  }

  Future<List<Map<String, dynamic>>> fetchAdminMarketersWithUnreadShared({
    required String token,
  }) async {
    final headers = _authHeaders(token);
    final url =
        '$baseUrl/admin/marketers/unread/'; // DRF: /api/admin/marketers/unread/

    final resp = await http.get(Uri.parse(url), headers: headers);
    if (resp.statusCode == 200) {
      final Map<String, dynamic> result =
          jsonDecode(resp.body) as Map<String, dynamic>;
      final marketers = <Map<String, dynamic>>[];
      if (result['marketers'] is List) {
        for (final item in (result['marketers'] as List)) {
          if (item is Map<String, dynamic>) {
            if (item['profile_image'] != null) {
              item['profile_image'] =
                  _absUrl(item['profile_image']?.toString());
            }
            marketers.add(Map<String, dynamic>.from(item));
          }
        }
      }
      return marketers;
    } else if (resp.statusCode == 403) {
      throw Exception('Forbidden: admin-only endpoint.');
    } else if (resp.statusCode == 401) {
      throw Exception('Authentication failed (401): ${resp.body}');
    } else {
      throw Exception(
          'Failed to fetch admin marketer chat list: ${resp.statusCode} ${resp.body}');
    }
  }

// ============================================================================
// CLIENT CHAT API METHODS
// ============================================================================
  Future<Map<String, dynamic>> getClientChatMessages({
    required String token,
    int page = 1,
    int pageSize = 50,
    int? lastMsgId,
    int? companyId,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    if (lastMsgId != null) {
      params['last_msg_id'] = lastMsgId.toString();
    }

    if (companyId != null) {
      params['company_id'] = companyId.toString();
    }

    final uri =
        Uri.parse('$baseUrl/client/chat/').replace(queryParameters: params);

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);

        // Normalize file URLs if present
        if (data['results'] is List) {
          for (var msg in data['results']) {
            if (msg is Map && msg['file_url'] != null) {
              final fileUrl = msg['file_url'].toString();
              if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                msg['file_url'] = '$baseUrl$fileUrl';
              }
            }
          }
        }

        // Handle non-paginated response
        if (data['messages'] is List) {
          for (var msg in data['messages']) {
            if (msg is Map && msg['file_url'] != null) {
              final fileUrl = msg['file_url'].toString();
              if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                msg['file_url'] = '$baseUrl$fileUrl';
              }
            }
          }
        }

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to load messages: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching chat messages: $e');
    }
  }

  /// Get a single message by ID
  ///
  /// Returns detailed message information
  Future<Map<String, dynamic>> getClientChatMessageDetail({
    required String token,
    required int messageId,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/$messageId/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);

        // Normalize file URL
        if (data['file_url'] != null) {
          final fileUrl = data['file_url'].toString();
          if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
            data['file_url'] = '$baseUrl$fileUrl';
          }
        }

        return data;
      } else if (response.statusCode == 404) {
        throw Exception(
            'Message not found or you do not have permission to view it.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to load message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching message detail: $e');
    }
  }

  /// Send a new message to admin
  Future<Map<String, dynamic>> sendClientChatMessage({
    required String token,
    String? content,
    File? file,
    String messageType = 'enquiry',
    int? replyToId,
    int? companyId,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/send/');

    try {
      var request = http.MultipartRequest('POST', uri);

      // Add headers
      request.headers['Authorization'] = 'Token $token';
      request.headers['Accept'] = 'application/json';

      // Add fields
      if (content != null && content.isNotEmpty) {
        request.fields['content'] = content;
      } else {
        request.fields['content'] = '';
      }

      request.fields['message_type'] = messageType;

      if (replyToId != null) {
        request.fields['reply_to'] = replyToId.toString();
      }

      if (companyId != null) {
        request.fields['company_id'] = companyId.toString();
      }

      // Add file if provided
      if (file != null) {
        final mimeType =
            lookupMimeType(file.path) ?? 'application/octet-stream';
        final parts = mimeType.split('/');

        request.files.add(
          await http.MultipartFile.fromPath(
            'file',
            file.path,
            contentType: MediaType(parts[0], parts[1]),
          ),
        );
      }

      // Validate that either content or file is provided
      if ((content == null || content.isEmpty) && file == null) {
        throw Exception('Please provide either a message or attach a file.');
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 201) {
        final Map<String, dynamic> data = jsonDecode(response.body);

        // Normalize file URL in response
        if (data['message'] is Map && data['message']['file_url'] != null) {
          final fileUrl = data['message']['file_url'].toString();
          if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
            data['message']['file_url'] = '$baseUrl$fileUrl';
          }
        }

        return data;
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(
            errorData['errors']?.toString() ?? 'Invalid message data.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to send message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error sending message: $e');
    }
  }

  /// Delete a message (only within 30 minutes of sending)
  ///
  /// Returns true if deletion was successful
  Future<bool> deleteClientChatMessage({
    required String token,
    required int messageId,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/$messageId/delete/');

    try {
      final response = await http.delete(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        return true;
      } else if (response.statusCode == 404) {
        throw Exception(
            'Message not found or you do not have permission to delete it.');
      } else if (response.statusCode == 403) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['error'] ??
            'You can only delete messages within 30 minutes of sending.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to delete message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error deleting message: $e');
    }
  }

  /// Get unread message count and last message
  ///
  /// Returns unread count and last message data
  Future<Map<String, dynamic>> getClientChatUnreadCount({
    required String token,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/unread-count/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);

        // Ensure unread_count is an integer
        data['unread_count'] = (data['unread_count'] is int)
            ? data['unread_count']
            : int.tryParse(data['unread_count']?.toString() ?? '0') ?? 0;

        // Normalize file URL in last_message if present
        if (data['last_message'] is Map &&
            data['last_message']['file_url'] != null) {
          final fileUrl = data['last_message']['file_url'].toString();
          if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
            data['last_message']['file_url'] = '$baseUrl$fileUrl';
          }
        }

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to load unread count: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching unread count: $e');
    }
  }

  /// Mark messages as read
  Future<Map<String, dynamic>> markClientChatMessagesAsRead({
    required String token,
    List<int>? messageIds,
    bool markAll = false,
    int? companyId,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/mark-read/');

    try {
      final body = <String, dynamic>{};

      if (markAll) {
        body['mark_all'] = true;
      } else if (messageIds != null && messageIds.isNotEmpty) {
        body['message_ids'] = messageIds;
      } else {
        throw Exception('Please provide message_ids or set mark_all to true.');
      }

      if (companyId != null) body['company_id'] = companyId;

      final response = await http.post(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['error'] ??
            'Please provide message_ids or set mark_all to true.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to mark messages as read: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error marking messages as read: $e');
    }
  }

  /// Poll for new messages since last_msg_id
  Future<Map<String, dynamic>> pollClientChatMessages({
    required String token,
    int lastMsgId = 0,
    int? companyId,
  }) async {
    final params = <String, String>{'last_msg_id': lastMsgId.toString()};
    if (companyId != null) params['company_id'] = companyId.toString();

    final uri = Uri.parse('$baseUrl/client/chat/poll/')
        .replace(queryParameters: params);

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);

        // Normalize file URLs in new messages
        if (data['new_messages'] is List) {
          for (var msg in data['new_messages']) {
            if (msg is Map && msg['file_url'] != null) {
              final fileUrl = msg['file_url'].toString();
              if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                msg['file_url'] = '$baseUrl$fileUrl';
              }
            }
          }
        }

        // Ensure count is an integer
        data['count'] = (data['count'] is int)
            ? data['count']
            : int.tryParse(data['count']?.toString() ?? '0') ?? 0;

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to poll messages: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error polling messages: $e');
    }
  }

  /// Fetch list of companies for client chat explorer
  ///
  /// Returns: List of companies with {id, company_name, logo_url, last_message, last_message_date, unread_count}
  Future<List<Map<String, dynamic>>> getClientChatCompanies({
    required String token,
  }) async {
    final uri = Uri.parse('$baseUrl/client/chat/companies/');

    try {
      final response = await http.get(uri, headers: {
        'Authorization': 'Token $token',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      });

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);
        final List<Map<String, dynamic>> out = [];

        if (data['companies'] is List) {
          for (var c in data['companies']) {
            if (c is Map<String, dynamic>) {
              // Normalize logo url
              if (c['logo_url'] is String) {
                final logo = c['logo_url'].toString();
                if (logo.isNotEmpty && !logo.startsWith('http')) {
                  c['logo_url'] = '$baseUrl$logo';
                }
              }

              // Normalize nested last_message file_url if present
              if (c['last_message'] is Map &&
                  c['last_message']['file_url'] != null) {
                final fileUrl = c['last_message']['file_url'].toString();
                if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                  c['last_message']['file_url'] = '$baseUrl$fileUrl';
                }
              }

              out.add(Map<String, dynamic>.from(c));
            }
          }
        }

        return out;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load client chat companies: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching client chat companies: $e');
    }
  }

  // ============================================================================
  // MARKETER CHAT API METHODS
  // ============================================================================

  Future<Map<String, dynamic>> getMarketerChatMessages({
    required String token,
    int page = 1,
    int pageSize = 50,
    int? lastMsgId,
    int? companyId,
  }) async {
    final params = <String, String>{
      'page': page.toString(),
      'page_size': pageSize.toString(),
    };

    if (lastMsgId != null) {
      params['last_msg_id'] = lastMsgId.toString();
    }

    if (companyId != null) {
      params['company_id'] = companyId.toString();
    }

    final uri =
        Uri.parse('$baseUrl/marketers/chat/').replace(queryParameters: params);

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> payload =
            jsonDecode(response.body) as Map<String, dynamic>;
        final Map<String, dynamic> data =
            (payload['success'] == true && payload['data'] is Map)
                ? Map<String, dynamic>.from(payload['data'] as Map)
                : payload;

        void normalizeList(dynamic list) {
          if (list is List) {
            for (var msg in list) {
              if (msg is Map && msg['file_url'] != null) {
                final fileUrl = msg['file_url'].toString();
                if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                  msg['file_url'] = '$baseUrl$fileUrl';
                }
              }
            }
          }
        }

        normalizeList(data['results']);
        normalizeList(data['messages']);

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to load messages: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error fetching marketer chat messages: $e');
    }
  }

  Future<Map<String, dynamic>> sendMarketerChatMessage({
    required String token,
    String? content,
    PlatformFile? file,
    String messageType = 'enquiry',
    int? replyToId,
    int? companyId,
  }) async {
    final uri = Uri.parse('$baseUrl/marketers/chat/send/');

    try {
      final request = http.MultipartRequest('POST', uri)
        ..headers['Authorization'] = 'Token $token'
        ..headers['Accept'] = 'application/json';

      request.fields['content'] = content?.trim() ?? '';

      request.fields['message_type'] = messageType;

      if (companyId != null) {
        request.fields['company_id'] = companyId.toString();
      }

      if (replyToId != null) {
        request.fields['reply_to'] = replyToId.toString();
      }

      if (file != null) {
        File uploadedFile;
        if (file.bytes != null) {
          uploadedFile =
              await persistFileBytes(bytes: file.bytes!, fileName: file.name);
        } else if (file.readStream != null) {
          uploadedFile = await persistFileStream(
              stream: file.readStream!, fileName: file.name);
        } else if (file.path != null) {
          uploadedFile = File(file.path!);
        } else {
          throw Exception('Unable to read attachment.');
        }

        final mimeType =
            lookupMimeType(uploadedFile.path) ?? 'application/octet-stream';
        final parts = mimeType.split('/');
        final bytes = await uploadedFile.readAsBytes();
        request.files.add(
          http.MultipartFile.fromBytes(
            'file',
            bytes,
            filename: p.basename(uploadedFile.path),
            contentType: MediaType(parts.first, parts.last),
          ),
        );
      }

      if ((content == null || content.isEmpty) && file == null) {
        throw Exception('Please provide either a message or attach a file.');
      }

      final streamedResponse = await request.send();
      final response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 201) {
        final Map<String, dynamic> payload =
            jsonDecode(response.body) as Map<String, dynamic>;
        final Map<String, dynamic> data =
            (payload['success'] == true && payload['data'] is Map)
                ? Map<String, dynamic>.from(payload['data'] as Map)
                : payload;

        final message = data['message'];
        if (message is Map && message['file_url'] != null) {
          final fileUrl = message['file_url'].toString();
          if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
            message['file_url'] = '$baseUrl$fileUrl';
          }
        }
        return data;
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(
            errorData['errors']?.toString() ?? 'Invalid message data.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to send message: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error sending marketer chat message: $e');
    }
  }

  Future<Map<String, dynamic>> markMarketerChatMessagesAsRead({
    required String token,
    List<int>? messageIds,
    bool markAll = false,
  }) async {
    final uri = Uri.parse('$baseUrl/marketers/chat/mark-read/');

    try {
      final body = <String, dynamic>{};

      if (markAll) {
        body['mark_all'] = true;
      } else if (messageIds != null && messageIds.isNotEmpty) {
        body['message_ids'] = messageIds;
      } else {
        throw Exception('Please provide message_ids or set mark_all to true.');
      }

      final response = await http.post(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: jsonEncode(body),
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> payload =
            jsonDecode(response.body) as Map<String, dynamic>;
        final Map<String, dynamic> data =
            (payload['success'] == true && payload['data'] is Map)
                ? Map<String, dynamic>.from(payload['data'] as Map)
                : payload;
        return data;
      } else if (response.statusCode == 400) {
        final errorData = jsonDecode(response.body);
        throw Exception(errorData['error'] ??
            'Please provide message_ids or set mark_all to true.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to mark messages as read: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error marking marketer messages as read: $e');
    }
  }

  Future<Map<String, dynamic>> pollMarketerChatMessages({
    required String token,
    int lastMsgId = 0,
    int? companyId,
  }) async {
    final params = {'last_msg_id': lastMsgId.toString()};
    if (companyId != null) {
      params['company_id'] = companyId.toString();
    }
    final uri = Uri.parse('$baseUrl/marketers/chat/poll/')
        .replace(queryParameters: params);

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      );

      if (response.statusCode == 200) {
        final Map<String, dynamic> payload =
            jsonDecode(response.body) as Map<String, dynamic>;
        final Map<String, dynamic> data =
            (payload['success'] == true && payload['data'] is Map)
                ? Map<String, dynamic>.from(payload['data'] as Map)
                : payload;

        if (data['new_messages'] is List) {
          for (var msg in data['new_messages']) {
            if (msg is Map && msg['file_url'] != null) {
              final fileUrl = msg['file_url'].toString();
              if (fileUrl.isNotEmpty && !fileUrl.startsWith('http')) {
                msg['file_url'] = '$baseUrl$fileUrl';
              }
            }
          }
        }

        data['count'] = (data['count'] is int)
            ? data['count']
            : int.tryParse(data['count']?.toString() ?? '0') ?? 0;

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception('Failed to poll messages: ${response.statusCode}');
      }
    } catch (e) {
      throw Exception('Error polling marketer messages: $e');
    }
  }

  /// Helper: Get file type from file path
  String getFileType(String filePath) {
    final name = filePath.toLowerCase();

    if (name.endsWith('.jpg') ||
        name.endsWith('.jpeg') ||
        name.endsWith('.png') ||
        name.endsWith('.gif') ||
        name.endsWith('.webp')) {
      return 'image';
    } else if (name.endsWith('.pdf')) {
      return 'pdf';
    } else if (name.endsWith('.doc') || name.endsWith('.docx')) {
      return 'document';
    } else if (name.endsWith('.xls') || name.endsWith('.xlsx')) {
      return 'spreadsheet';
    } else if (name.endsWith('.zip') ||
        name.endsWith('.rar') ||
        name.endsWith('.7z')) {
      return 'archive';
    } else {
      return 'file';
    }
  }

  /// Helper: Format file size to human readable format
  String formatFileSize(int bytes) {
    if (bytes < 1024) return '$bytes B';
    if (bytes < 1024 * 1024) return '${(bytes / 1024).toStringAsFixed(1)} KB';
    if (bytes < 1024 * 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(1)} MB';
    }
    return '${(bytes / (1024 * 1024 * 1024)).toStringAsFixed(1)} GB';
  }

  /// Helper: Check if message can be deleted (within 30 minutes)
  bool canDeleteMessage(DateTime messageSentDate) {
    final now = DateTime.now();
    final difference = now.difference(messageSentDate);
    return difference.inMinutes <= 30;
  }

  Future<File> persistFileBytes({
    required List<int> bytes,
    required String? fileName,
  }) async {
    final tempDir = await getTemporaryDirectory();
    final safeName = fileName?.isNotEmpty == true
        ? fileName!
        : 'upload_${DateTime.now().millisecondsSinceEpoch}';
    final filePath = p.join(tempDir.path, safeName);
    final file = File(filePath);
    await file.writeAsBytes(bytes, flush: true);
    return file;
  }

  Future<File> persistFileStream({
    required Stream<List<int>> stream,
    required String? fileName,
  }) async {
    final tempDir = await getTemporaryDirectory();
    final safeName = fileName?.isNotEmpty == true
        ? fileName!
        : 'upload_${DateTime.now().millisecondsSinceEpoch}';
    final filePath = p.join(tempDir.path, safeName);
    final file = File(filePath);
    final sink = file.openWrite();
    await stream.pipe(sink);
    await sink.close();
    return file;
  }

  // =========================================================================
  // CLIENT COMPANY PORTFOLIO API METHODS (my_companies.html & my_company_portfolio.html)
  // =========================================================================

  /// Fetch all companies for the current client with stats and allocation counts
  /// GET /api/clients/my-companies/
  /// Returns: List of companies with rank, total_invested, allocation counts, marketer info
  Future<Map<String, dynamic>> getClientMyCompanies({
    required String token,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/api/clients/my-companies/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data =
            jsonDecode(response.body) as Map<String, dynamic>;

        // Normalize company logos if present
        if (data['companies'] is List) {
          for (var company in (data['companies'] as List)) {
            if (company is Map && company['logo_url'] != null) {
              final logoUrl = company['logo_url'].toString();
              if (logoUrl.isNotEmpty && !logoUrl.startsWith('http')) {
                company['logo_url'] = _absUrl(logoUrl);
              }
            }
          }
        }

        return data;
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load companies: ${response.statusCode} ${response.body}');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please check your connection.');
    } catch (e) {
      throw Exception('Error fetching companies: $e');
    }
  }

  /// Fetch comprehensive portfolio data for a specific company
  /// GET /api/clients/company/{company_id}/portfolio/
  /// Returns: Company details, stats, properties, appreciation data, payment history, estates count
  Future<Map<String, dynamic>> getClientCompanyPortfolio({
    required String token,
    required int companyId,
    Duration timeout = const Duration(seconds: 20),
  }) async {
    final uri = Uri.parse('$baseUrl/api/clients/company/$companyId/portfolio/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data =
            jsonDecode(response.body) as Map<String, dynamic>;

        // Normalize company logo
        if (data['company'] is Map && data['company']['logo_url'] != null) {
          final logoUrl = data['company']['logo_url'].toString();
          if (logoUrl.isNotEmpty && !logoUrl.startsWith('http')) {
            data['company']['logo_url'] = _absUrl(logoUrl);
          }
        }

        // Normalize estate logos in properties
        if (data['properties'] is List) {
          for (var prop in (data['properties'] as List)) {
            if (prop is Map && prop['logo_url'] != null) {
              final logoUrl = prop['logo_url'].toString();
              if (logoUrl.isNotEmpty && !logoUrl.startsWith('http')) {
                prop['logo_url'] = _absUrl(logoUrl);
              }
            }
          }
        }

        // Normalize estate logos in appreciation_data
        if (data['appreciation_data'] is List) {
          for (var appreciation in (data['appreciation_data'] as List)) {
            if (appreciation is Map && appreciation['logo_url'] != null) {
              final logoUrl = appreciation['logo_url'].toString();
              if (logoUrl.isNotEmpty && !logoUrl.startsWith('http')) {
                appreciation['logo_url'] = _absUrl(logoUrl);
              }
            }
          }
        }

        return data;
      } else if (response.statusCode == 403) {
        throw Exception('You do not have access to this company.');
      } else if (response.statusCode == 404) {
        throw Exception('Company not found.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load portfolio: ${response.statusCode} ${response.body}');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please check your connection.');
    } catch (e) {
      throw Exception('Error fetching portfolio: $e');
    }
  }

  /// Fetch detailed transaction information and payment breakdown
  /// GET /api/clients/company/transaction/{transaction_id}/
  /// Returns: Transaction details with allocation info, payment plan, installment breakdown
  Future<Map<String, dynamic>> getClientCompanyTransactionDetail({
    required String token,
    required int transactionId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri =
        Uri.parse('$baseUrl/api/clients/company/transaction/$transactionId/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(timeout);

      if (response.statusCode == 200) {
        return jsonDecode(response.body) as Map<String, dynamic>;
      } else if (response.statusCode == 403) {
        throw Exception('You do not have access to this transaction.');
      } else if (response.statusCode == 404) {
        throw Exception('Transaction not found.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load transaction: ${response.statusCode} ${response.body}');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please check your connection.');
    } catch (e) {
      throw Exception('Error fetching transaction: $e');
    }
  }

  /// Fetch payment history for a specific transaction
  /// GET /api/clients/company/payment-history/?transaction_id={id}
  /// Returns: List of payment records with dates, amounts, references, and statuses
  Future<List<dynamic>> getClientCompanyPaymentHistory({
    required String token,
    required int transactionId,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final uri = Uri.parse('$baseUrl/api/clients/company/payment-history/')
        .replace(queryParameters: {'transaction_id': transactionId.toString()});

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data =
            jsonDecode(response.body) as Map<String, dynamic>;

        // Handle both direct list and wrapped response
        if (data['payments'] is List) {
          return data['payments'] as List<dynamic>;
        }

        return <dynamic>[];
      } else if (response.statusCode == 404) {
        throw Exception('Transaction not found.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load payment history: ${response.statusCode} ${response.body}');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please check your connection.');
    } catch (e) {
      throw Exception('Error fetching payment history: $e');
    }
  }

  /// Download receipt for a payment by reference code
  /// GET /api/clients/company/receipt/{reference}/
  /// Returns: Receipt data (reference, amount, date, estate, download_url)
  Future<Map<String, dynamic>> getClientCompanyReceipt({
    required String token,
    required String reference,
    Duration timeout = const Duration(seconds: 15),
  }) async {
    final safeRef = Uri.encodeComponent(reference);
    final uri = Uri.parse('$baseUrl/api/clients/company/receipt/$safeRef/');

    try {
      final response = await http.get(
        uri,
        headers: {
          'Authorization': 'Token $token',
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
      ).timeout(timeout);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data =
            jsonDecode(response.body) as Map<String, dynamic>;

        // Normalize download URL if present
        if (data['download_url'] != null) {
          final downloadUrl = data['download_url'].toString();
          if (downloadUrl.isNotEmpty && !downloadUrl.startsWith('http')) {
            data['download_url'] = _absUrl(downloadUrl);
          }
        }

        return data;
      } else if (response.statusCode == 404) {
        throw Exception('Receipt not found.');
      } else if (response.statusCode == 403) {
        throw Exception('You do not have access to this receipt.');
      } else if (response.statusCode == 401) {
        throw Exception('Authentication failed. Please login again.');
      } else {
        throw Exception(
            'Failed to load receipt: ${response.statusCode} ${response.body}');
      }
    } on TimeoutException {
      throw Exception('Request timed out. Please check your connection.');
    } catch (e) {
      throw Exception('Error fetching receipt: $e');
    }
  }

  /// Download receipt file by reference code
  /// Query param variant: GET /api/clients/company/receipt/?reference={code}
  /// Returns: PDF file bytes
  Future<File> downloadClientCompanyReceiptPdf({
    required String token,
    required String reference,
    void Function(int, int)? onProgress,
    bool openAfterDownload = false,
    Duration timeout = const Duration(seconds: 60),
  }) async {
    final safeRef = Uri.encodeComponent(reference);
    final base = baseUrl.endsWith('/')
        ? baseUrl.substring(0, baseUrl.length - 1)
        : baseUrl;
    final url = '$base/api/clients/company/receipt/$safeRef/';

    final dir = await getTemporaryDirectory();
    final filePath = '${dir.path}/receipt_$safeRef.pdf';
    final file = File(filePath);

    try {
      final resp = await _dio.get<List<int>>(
        url,
        options: Options(
          headers: {'Authorization': 'Token $token'},
          responseType: ResponseType.bytes,
          validateStatus: (s) => s != null && s < 500,
        ),
        onReceiveProgress: (rec, total) {
          if (onProgress != null) onProgress(rec, total);
        },
      ).timeout(timeout);

      final status = resp.statusCode ?? 0;
      if (status == 200 && resp.data != null && resp.data!.isNotEmpty) {
        await file.writeAsBytes(resp.data!, flush: true);
        if (openAfterDownload) await OpenFile.open(file.path);
        return file;
      } else if (status == 404) {
        throw Exception('Receipt not found');
      } else if (status == 403) {
        throw Exception('Access denied to this receipt');
      } else {
        final text = resp.data != null ? String.fromCharCodes(resp.data!) : '';
        throw Exception('Failed to download (status: $status) $text');
      }
    } on DioError catch (e) {
      throw Exception('Network error: ${e.message}');
    }
  }
}
