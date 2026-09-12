import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../models/auth_session.dart';
import '../repositories/auth_repository.dart';
import 'app_providers.dart';

enum AuthStatus { unknown, unauthenticated, authenticated }

class AuthState {
  const AuthState({
    required this.status,
    this.user,
    this.error,
    this.busy = false,
  });

  final AuthStatus status;
  final AuthUser? user;
  final String? error;
  final bool busy;

  bool get isAuthenticated => status == AuthStatus.authenticated;

  AuthState copyWith({
    AuthStatus? status,
    AuthUser? user,
    String? error,
    bool? busy,
    bool clearError = false,
  }) {
    return AuthState(
      status: status ?? this.status,
      user: user ?? this.user,
      error: clearError ? null : (error ?? this.error),
      busy: busy ?? this.busy,
    );
  }
}

final authControllerProvider =
    NotifierProvider<AuthController, AuthState>(AuthController.new);

class AuthController extends Notifier<AuthState> {
  @override
  AuthState build() {
    _restore();
    return const AuthState(status: AuthStatus.unknown);
  }

  AuthRepository get _repository => ref.read(authRepositoryProvider);

  Future<void> _restore() async {
    final hasSession = await ref.read(tokenStoreProvider).hasSession;
    if (!hasSession) {
      state = const AuthState(status: AuthStatus.unauthenticated);
      return;
    }
    try {
      final user = await _repository.me();
      state = AuthState(status: AuthStatus.authenticated, user: user);
    } catch (_) {
      state = const AuthState(status: AuthStatus.unauthenticated);
    }
  }

  Future<bool> login(String email, String password) async {
    state = state.copyWith(busy: true, clearError: true);
    try {
      final session = await _repository.login(email, password);
      state = AuthState(status: AuthStatus.authenticated, user: session.user);
      return true;
    } catch (error) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: error.toString(),
      );
      return false;
    }
  }

  Future<bool> register(String email, String password, String? fullName) async {
    state = state.copyWith(busy: true, clearError: true);
    try {
      final session = await _repository.register(
        email: email,
        password: password,
        fullName: fullName,
      );
      state = AuthState(status: AuthStatus.authenticated, user: session.user);
      return true;
    } catch (error) {
      state = AuthState(
        status: AuthStatus.unauthenticated,
        error: error.toString(),
      );
      return false;
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    state = const AuthState(status: AuthStatus.unauthenticated);
  }
}
