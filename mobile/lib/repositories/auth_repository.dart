import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../core/storage/token_store.dart';
import '../models/auth_session.dart';
import '../providers/app_providers.dart';

class AuthRepository {
  AuthRepository(this._api, this._tokens);

  final ApiClient _api;
  final TokenStore _tokens;

  Future<AuthSession> login(String email, String password) async {
    final json = await _api.postJson(
      '/auth/login',
      body: {'email': email, 'password': password},
    );
    return _persist(json);
  }

  Future<AuthSession> register({
    required String email,
    required String password,
    String? fullName,
  }) async {
    final json = await _api.postJson(
      '/auth/register',
      body: {'email': email, 'password': password, 'full_name': fullName},
    );
    return _persist(json);
  }

  Future<AuthUser> me() async {
    final json = await _api.getJson('/auth/me');
    return AuthUser.fromJson(json);
  }

  Future<void> logout() async {
    final refresh = await _tokens.refreshToken;
    if (refresh != null) {
      try {
        await _api.post('/auth/logout', body: {'refresh_token': refresh});
      } catch (_) {
        // Best-effort server-side revocation; always clear locally.
      }
    }
    await _tokens.clear();
  }

  Future<AuthSession> _persist(Map<String, dynamic> json) async {
    final tokens = AuthTokens.fromJson(
      (json['tokens'] as Map<String, dynamic>?) ?? const {},
    );
    final user = AuthUser.fromJson(
      (json['user'] as Map<String, dynamic>?) ?? const {},
    );
    await _tokens.saveTokens(
      accessToken: tokens.accessToken,
      refreshToken: tokens.refreshToken,
    );
    return AuthSession(user: user, tokens: tokens);
  }
}

final authRepositoryProvider = Provider<AuthRepository>(
  (ref) => AuthRepository(
    ref.watch(apiClientProvider),
    ref.watch(tokenStoreProvider),
  ),
);
