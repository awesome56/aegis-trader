import 'package:aegis_trader_mobile/core/config/app_config.dart';
import 'package:aegis_trader_mobile/models/health.dart';
import 'package:aegis_trader_mobile/models/system_status.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('AppConfig', () {
    test('composes the versioned REST base URL', () {
      expect(AppConfig.restBaseUrl, endsWith(AppConfig.apiPrefix));
    });
  });

  group('HealthStatus', () {
    test('parses components', () {
      final status = HealthStatus.fromJson({
        'status': 'degraded',
        'service': 'Aegis Trader',
        'version': '0.1.0',
        'environment': 'test',
        'components': [
          {'name': 'database', 'status': 'healthy', 'latency_ms': 1.5},
          {'name': 'redis', 'status': 'unhealthy'},
        ],
      });

      expect(status.status, 'degraded');
      expect(status.components, hasLength(2));
      expect(status.components.first.isHealthy, isTrue);
      expect(status.components.last.isHealthy, isFalse);
    });
  });

  group('SystemStatus', () {
    test('detects paper mode and live-trading interlock', () {
      final status = SystemStatus.fromJson({
        'app_name': 'Aegis Trader',
        'version': '0.1.0',
        'environment': 'test',
        'trading_mode': 'paper',
        'live_trading_enabled': false,
        'live_trading_guard': {
          'allowed': false,
          'missing_requirements': ['TRADING_MODE must be \'live\''],
        },
        'broker_provider': 'paper',
        'market_data_provider': 'mock',
        'agent_enabled': false,
        'kill_switch_state': 'TRADING_ENABLED',
      });

      expect(status.isPaperTrading, isTrue);
      expect(status.isEmergencyStopped, isFalse);
      expect(status.liveTradingGuard.allowed, isFalse);
      expect(status.liveTradingGuard.missingRequirements, hasLength(1));
    });
  });
}
