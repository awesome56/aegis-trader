import 'dart:convert';
import 'dart:io';

import 'package:path_provider/path_provider.dart';

import '../errors/app_exception.dart';

/// Simple JSON-file cache used for offline reading of previously fetched data.
///
/// This is intentionally dependency-light for Phase 1. A structured embedded
/// database (Drift/Isar) is introduced in Phase 10 when offline querying of
/// history becomes a requirement.
class LocalCache {
  LocalCache();

  Future<File> _fileFor(String key) async {
    final dir = await getApplicationSupportDirectory();
    final cacheDir = Directory('${dir.path}/cache');
    if (!cacheDir.existsSync()) {
      await cacheDir.create(recursive: true);
    }
    return File('${cacheDir.path}/$key.json');
  }

  Future<dynamic> readJson(String key) async {
    try {
      final file = await _fileFor(key);
      if (!file.existsSync()) return null;
      final raw = await file.readAsString();
      if (raw.isEmpty) return null;
      return jsonDecode(raw);
    } on FileSystemException catch (error) {
      throw StorageException(error.message);
    }
  }

  Future<void> writeJson(String key, Object? value) async {
    try {
      final file = await _fileFor(key);
      await file.writeAsString(jsonEncode(value));
    } on FileSystemException catch (error) {
      throw StorageException(error.message);
    }
  }

  Future<void> remove(String key) async {
    final file = await _fileFor(key);
    if (file.existsSync()) {
      await file.delete();
    }
  }
}
