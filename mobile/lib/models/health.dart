/// Health/status models returned by the backend.
class ComponentHealth {
  const ComponentHealth({
    required this.name,
    required this.status,
    this.latencyMs,
    this.detail,
  });

  final String name;
  final String status;
  final double? latencyMs;
  final String? detail;

  bool get isHealthy => status == 'healthy';

  factory ComponentHealth.fromJson(Map<String, dynamic> json) {
    return ComponentHealth(
      name: json['name'] as String? ?? 'unknown',
      status: json['status'] as String? ?? 'unhealthy',
      latencyMs: (json['latency_ms'] as num?)?.toDouble(),
      detail: json['detail'] as String?,
    );
  }
}

class HealthStatus {
  const HealthStatus({
    required this.status,
    required this.service,
    required this.version,
    required this.environment,
    required this.components,
  });

  final String status;
  final String service;
  final String version;
  final String environment;
  final List<ComponentHealth> components;

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    final components = (json['components'] as List<dynamic>? ?? const [])
        .whereType<Map<String, dynamic>>()
        .map(ComponentHealth.fromJson)
        .toList();
    return HealthStatus(
      status: json['status'] as String? ?? 'unknown',
      service: json['service'] as String? ?? 'Aegis Trader',
      version: json['version'] as String? ?? '-',
      environment: json['environment'] as String? ?? '-',
      components: components,
    );
  }
}
