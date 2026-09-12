import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

import '../core/config/app_config.dart';

/// Typed realtime event envelope: `{ "event": "...", "timestamp": "...", "data": {...} }`.
class AppEvent {
  const AppEvent({
    required this.event,
    required this.timestamp,
    required this.data,
  });

  final String event;
  final String? timestamp;
  final Map<String, dynamic> data;

  factory AppEvent.fromJson(Map<String, dynamic> json) {
    return AppEvent(
      event: json['event'] as String? ?? 'unknown',
      timestamp: json['timestamp'] as String?,
      data: (json['data'] as Map<String, dynamic>?) ?? const {},
    );
  }
}

enum SocketState { disconnected, connecting, connected }

/// Authenticated WebSocket client with exponential-backoff reconnection.
///
/// Phase 1 establishes the transport and typed envelopes; feature-specific
/// subscription wiring lands in Phase 4 together with the backend channels.
class WebSocketService {
  WebSocketService({this.path = '/ws'});

  final String path;

  WebSocketChannel? _channel;
  String? _token;
  bool _closedByUser = false;
  int _attempt = 0;
  final _events = StreamController<AppEvent>.broadcast();
  final _state = ValueNotifier<SocketState>(SocketState.disconnected);

  Stream<AppEvent> get events => _events.stream;
  ValueListenable<SocketState> get state => _state;

  Future<void> connect(String token) async {
    _token = token;
    _closedByUser = false;
    await _open();
  }

  Future<void> _open() async {
    _state.value = SocketState.connecting;
    final uri = Uri.parse('${AppConfig.wsBaseUrl}$path?token=$_token');
    try {
      final channel = WebSocketChannel.connect(uri);
      await channel.ready;
      _channel = channel;
      _attempt = 0;
      _state.value = SocketState.connected;
      channel.stream.listen(
        _handleMessage,
        onDone: _handleDisconnect,
        onError: (_) => _handleDisconnect(),
        cancelOnError: true,
      );
    } catch (_) {
      _handleDisconnect();
    }
  }

  void _handleMessage(dynamic raw) {
    if (raw is! String) return;
    try {
      final decoded = jsonDecode(raw);
      if (decoded is Map<String, dynamic>) {
        _events.add(AppEvent.fromJson(decoded));
      }
    } catch (_) {
      // Ignore malformed frames rather than tearing down the socket.
    }
  }

  void _handleDisconnect() {
    _state.value = SocketState.disconnected;
    _channel = null;
    if (_closedByUser) return;

    _attempt = (_attempt + 1).clamp(1, 6);
    final delay = Duration(seconds: 1 << (_attempt - 1));
    Future<void>.delayed(delay, () {
      if (!_closedByUser) {
        _open();
      }
    });
  }

  Future<void> disconnect() async {
    _closedByUser = true;
    await _channel?.sink.close();
    _channel = null;
    _state.value = SocketState.disconnected;
  }

  Future<void> dispose() async {
    await disconnect();
    await _events.close();
    _state.dispose();
  }
}
