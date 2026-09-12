import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/network/api_client.dart';
import '../models/health.dart';
import '../models/system_status.dart';
import '../providers/app_providers.dart';

class SystemRepository {
  SystemRepository(this._api);

  final ApiClient _api;

  Future<HealthStatus> fetchHealth() async {
    final json = await _api.getJson('/health');
    return HealthStatus.fromJson(json);
  }

  Future<SystemStatus> fetchStatus() async {
    final json = await _api.getJson('/system/status');
    return SystemStatus.fromJson(json);
  }
}

final systemRepositoryProvider = Provider<SystemRepository>(
  (ref) => SystemRepository(ref.watch(apiClientProvider)),
);

final healthProvider = FutureProvider.autoDispose<HealthStatus>(
  (ref) => ref.watch(systemRepositoryProvider).fetchHealth(),
);

final systemStatusProvider = FutureProvider<SystemStatus>(
  (ref) => ref.watch(systemRepositoryProvider).fetchStatus(),
);
