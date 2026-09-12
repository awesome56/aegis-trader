/// System/trading status model returned by `GET /system/status`.
class LiveTradingGuard {
  const LiveTradingGuard({
    required this.allowed,
    required this.missingRequirements,
  });

  final bool allowed;
  final List<String> missingRequirements;

  factory LiveTradingGuard.fromJson(Map<String, dynamic> json) {
    return LiveTradingGuard(
      allowed: json['allowed'] as bool? ?? false,
      missingRequirements: (json['missing_requirements'] as List<dynamic>? ?? const [])
          .map((item) => item.toString())
          .toList(),
    );
  }
}

class SystemStatus {
  const SystemStatus({
    required this.appName,
    required this.version,
    required this.environment,
    required this.tradingMode,
    required this.liveTradingEnabled,
    required this.liveTradingGuard,
    required this.brokerProvider,
    required this.marketDataProvider,
    required this.agentEnabled,
    required this.killSwitchState,
  });

  final String appName;
  final String version;
  final String environment;
  final String tradingMode;
  final bool liveTradingEnabled;
  final LiveTradingGuard liveTradingGuard;
  final String brokerProvider;
  final String marketDataProvider;
  final bool agentEnabled;
  final String killSwitchState;

  bool get isPaperTrading => tradingMode == 'paper';
  bool get isEmergencyStopped => killSwitchState == 'EMERGENCY_STOP';

  factory SystemStatus.fromJson(Map<String, dynamic> json) {
    return SystemStatus(
      appName: json['app_name'] as String? ?? 'Aegis Trader',
      version: json['version'] as String? ?? '-',
      environment: json['environment'] as String? ?? '-',
      tradingMode: json['trading_mode'] as String? ?? 'paper',
      liveTradingEnabled: json['live_trading_enabled'] as bool? ?? false,
      liveTradingGuard: LiveTradingGuard.fromJson(
        (json['live_trading_guard'] as Map<String, dynamic>?) ?? const {},
      ),
      brokerProvider: json['broker_provider'] as String? ?? '-',
      marketDataProvider: json['market_data_provider'] as String? ?? '-',
      agentEnabled: json['agent_enabled'] as bool? ?? false,
      killSwitchState: json['kill_switch_state'] as String? ?? 'TRADING_ENABLED',
    );
  }
}
