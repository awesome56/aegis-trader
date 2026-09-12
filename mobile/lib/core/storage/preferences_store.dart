import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Wrapper over SharedPreferences for lightweight, non-sensitive preferences.
class PreferencesStore {
  PreferencesStore(this._prefs);

  final SharedPreferences _prefs;

  static const _themeKey = 'aegis.theme_mode';

  ThemeMode get themeMode {
    final value = _prefs.getString(_themeKey);
    return switch (value) {
      'light' => ThemeMode.light,
      'dark' => ThemeMode.dark,
      _ => ThemeMode.system,
    };
  }

  Future<void> setThemeMode(ThemeMode mode) =>
      _prefs.setString(_themeKey, mode.name);
}
