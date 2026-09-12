# Aegis Trader — Mobile

Flutter monitoring and control client. The app talks **only** to the Aegis
Trader backend; it never holds broker credentials or calls a broker directly.

The app is linked to the production backend at
**`https://rider.awesometech.com.ng`** (WebSocket `wss://rider.awesometech.com.ng`)
via the defaults in `lib/core/config/app_config.dart`.

## Requirements

- Flutter SDK 3.22+ (stable channel)
- Dart 3.4+

## Configure the backend URL

The backend URL is injected at build time. Two define files are provided:

| File | Target |
|------|--------|
| `dart_defines/prod.json` | `https://rider.awesometech.com.ng` (Lenovo server) |
| `dart_defines/dev.json`  | `http://10.0.2.2:8000` (local Android emulator) |

```bash
# Production (Lenovo server)
flutter run  --dart-define-from-file=dart_defines/prod.json
flutter build apk --release --dart-define-from-file=dart_defines/prod.json

# Local development
flutter run --dart-define-from-file=dart_defines/dev.json
```

For a physical device on the same LAN as your dev machine, override with
`--dart-define=API_BASE_URL=http://<your-lan-ip>:8000`.

## Run

```bash
flutter pub get
flutter run
```

## Verify

```bash
flutter analyze
flutter test
```

## Phase 1 scope

- Riverpod, GoRouter, Dio, secure token storage, shared preferences, local JSON cache
- Light/dark Material 3 fintech theme
- Bottom-navigation shell: Dashboard / Portfolio / Markets / Agent / More
- Reusable loading / error / empty / placeholder widgets
- Real system-status and health data from the backend on Dashboard and Settings
- Account sign-in / bootstrap-registration flow against the backend

Trading data (positions, orders, agent decisions, risk, backtests) is
intentionally not fabricated; those screens are labelled with their delivery
phase until the corresponding backend phase is complete.
