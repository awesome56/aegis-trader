/// Compile-time environment configuration.
///
/// Values are injected with `--dart-define` (or `--dart-define-from-file`).
/// The defaults target the production backend on the Lenovo server:
///   flutter run --dart-define-from-file=dart_defines/prod.json
///
/// For local development use the bundled dev defines:
///   flutter run --dart-define-from-file=dart_defines/dev.json
class AppConfig {
  const AppConfig._();

  static const String environment = String.fromEnvironment(
    'ENVIRONMENT',
    defaultValue: 'production',
  );

  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'https://traderbackend.awesometech.com.ng',
  );

  static const String wsBaseUrl = String.fromEnvironment(
    'WS_BASE_URL',
    defaultValue: 'wss://traderbackend.awesometech.com.ng',
  );

  static const String apiPrefix = '/api/v1';

  static String get restBaseUrl => '$apiBaseUrl$apiPrefix';

  static bool get isProduction => environment == 'production';
}
