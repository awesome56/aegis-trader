/// Application exception hierarchy surfaced to the UI layer.
sealed class AppException implements Exception {
  const AppException(this.message);

  final String message;

  @override
  String toString() => message;
}

/// A non-2xx response from the backend.
class ApiException extends AppException {
  const ApiException(super.message, {this.statusCode, this.code, this.details});

  final int? statusCode;
  final String? code;
  final Map<String, dynamic>? details;

  factory ApiException.fromEnvelope(int? statusCode, Map<String, dynamic> body) {
    final error = body['error'];
    if (error is Map<String, dynamic>) {
      return ApiException(
        (error['message'] as String?) ?? 'Request failed',
        statusCode: statusCode,
        code: error['code'] as String?,
        details: error['details'] as Map<String, dynamic>?,
      );
    }
    return ApiException('Request failed', statusCode: statusCode);
  }
}

/// Connectivity/timeout/parse failure.
class NetworkException extends AppException {
  const NetworkException([super.message = 'Network unavailable']);
}

/// Local persistence failure.
class StorageException extends AppException {
  const StorageException([super.message = 'Local storage error']);
}
