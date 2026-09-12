import 'package:dio/dio.dart';

import '../config/app_config.dart';
import '../errors/app_exception.dart';
import '../storage/token_store.dart';

/// Attaches the bearer access token to outgoing requests when available.
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this._tokens);

  final TokenStore _tokens;

  @override
  Future<void> onRequest(
    RequestOptions options,
    RequestInterceptorHandler handler,
  ) async {
    final token = await _tokens.accessToken;
    if (token != null && token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

/// Translates transport and API errors into the app exception hierarchy.
class ErrorInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    final response = err.response;
    final data = response?.data;

    if (data is Map && data['error'] is Map) {
      handler.reject(
        DioException(
          requestOptions: err.requestOptions,
          response: response,
          error: ApiException.fromEnvelope(
            response?.statusCode,
            Map<String, dynamic>.from(data),
          ),
        ),
      );
      return;
    }

    final mapped = switch (err.type) {
      DioExceptionType.connectionTimeout ||
      DioExceptionType.sendTimeout ||
      DioExceptionType.receiveTimeout ||
      DioExceptionType.connectionError =>
        const NetworkException('Cannot reach the trading backend'),
      _ => NetworkException(err.message ?? 'Network error'),
    };

    handler.reject(
      DioException(
        requestOptions: err.requestOptions,
        response: response,
        error: mapped,
      ),
    );
  }
}

/// Thin, typed wrapper around Dio used by all repositories.
class ApiClient {
  ApiClient(this._dio);

  final Dio _dio;

  factory ApiClient.create({required TokenStore tokenStore}) {
    final dio = Dio(
      BaseOptions(
        baseUrl: AppConfig.restBaseUrl,
        connectTimeout: const Duration(seconds: 10),
        receiveTimeout: const Duration(seconds: 20),
        sendTimeout: const Duration(seconds: 10),
        contentType: Headers.jsonContentType,
        headers: {'Accept': 'application/json'},
      ),
    );
    dio.interceptors.addAll([AuthInterceptor(tokenStore), ErrorInterceptor()]);
    return ApiClient(dio);
  }

  Future<Map<String, dynamic>> getJson(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await _request(() => _dio.get<dynamic>(path, queryParameters: query));
    return _asMap(response.data);
  }

  Future<List<dynamic>> getList(
    String path, {
    Map<String, dynamic>? query,
  }) async {
    final response = await _request(() => _dio.get<dynamic>(path, queryParameters: query));
    final data = response.data;
    if (data is List) return data;
    throw const NetworkException('Unexpected response shape');
  }

  Future<Map<String, dynamic>> postJson(
    String path, {
    Object? body,
  }) async {
    final response = await _request(() => _dio.post<dynamic>(path, data: body));
    return _asMap(response.data);
  }

  Future<void> post(String path, {Object? body}) async {
    await _request(() => _dio.post<dynamic>(path, data: body));
  }

  Future<Response<dynamic>> _request(Future<Response<dynamic>> Function() run) async {
    try {
      return await run();
    } on DioException catch (error) {
      final mapped = error.error;
      if (mapped is AppException) {
        throw mapped;
      }
      throw const NetworkException();
    }
  }

  Map<String, dynamic> _asMap(dynamic data) {
    if (data is Map) return Map<String, dynamic>.from(data);
    throw const NetworkException('Unexpected response shape');
  }
}
