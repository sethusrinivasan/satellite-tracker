# Mobile & Native Client Applications

This directory houses native, first-principles client applications for mobile and handheld operating systems. Each platform implementation follows idiomatic design patterns, modern UI toolkits, and offline-capable orbital propagation engines.

---

## Architecture Overview

```
mobile/
├── android/            # Native Android (Kotlin, Jetpack Compose, Material 3)
│   ├── app/
│   │   ├── src/main/java/com/sattrack/
│   │   │   ├── data/        # CelesTrak client, Repositories, Offline cache
│   │   │   ├── domain/      # Pure Kotlin SGP4 engine, Pass predictor, Local AI parser
│   │   │   ├── ui/          # Compose screens, 3D Globe, Canvas orbit maps
│   │   │   └── viewmodel/   # State management & coroutine flows
│   │   └── src/test/        # Unit tests for orbital propagation & pass predictions
│   ├── build.gradle.kts
│   └── gradlew
├── ios/                # [Planned] Native iOS (Swift, SwiftUI, Metal)
└── windows/            # [Planned] Native Windows (WinUI 3, C# / C++)
```

---

## Native Android Application (`mobile/android`)

The Android application is built from first principles with **zero external telemetry** and **complete offline orbital propagation capability**.

### Key Modules & Capabilities
1. **Orbital Propagation Engine (`domain/sgp4/Sgp4Engine.kt`)**:
   - High-precision SGP4/SDP4 mathematical model implemented in pure Kotlin.
   - Computes Earth-Centered Inertial (ECI) coordinates, Greenwich Mean Sidereal Time (GMST), sub-satellite ground track (geodetic latitude, longitude, altitude), and orbital velocity.
2. **Topocentric Pass Predictor (`domain/pass/PassPredictorEngine.kt`)**:
   - Converts ECI satellite position and velocity into topocentric Horizon coordinates (Azimuth, Elevation, Range, Range Rate) relative to the observer's geographic position.
   - Predicts upcoming passes, Rise-of-Pass (AOS), Maximum Elevation (PCA), and Loss-of-Signal (LOS).
3. **Local Query Parser (`domain/ai/LocalQueryParser.kt`)**:
   - Offline heuristic Natural Language Understanding (NLU) engine supporting complex catalog queries (e.g., "Find active space stations", "Upcoming passes over London", "Starlink constellation").
4. **Modern Jetpack Compose UI (`ui/`)**:
   - Fully dynamic Material 3 dark/light themes.
   - Hardware-accelerated 2D equirectangular orbit map canvas (`OrbitMapView.kt`).
   - Hardware-accelerated 3D globe visualization (`Globe3DView.kt`).
   - Live telemetry bottom sheet with real-time altitude, velocity, and doppler data.

---

## Building & Testing

### Prerequisites
- **JDK 17** (e.g. OpenJDK 17 or Eclipse Temurin)
- **Android SDK Platform 35** and **Build-Tools 35.0.0**
- `ANDROID_HOME` environment variable configured

### Quick Commands

All tasks can be executed via Gradle wrapper or root project npm scripts:

| Task | Gradle Command (`mobile/android/`) | Root npm Command |
|---|---|---|
| **Run Unit Tests** | `./gradlew test` | `npm run android:test` |
| **Build Debug APK** | `./gradlew assembleDebug` | `npm run android:dev` |
| **Build Release AAB (Play Store)** | `./gradlew bundleRelease` | `npm run android:build:aab` |
| **Build Release APK (Amazon / Sideload)** | `./gradlew assembleRelease` | `npm run android:build:apk` |
| **Lint & Quality Check** | `./gradlew lint` | — |

---

## Signing Configuration

Production signing automatically detects keystores in standard project locations:
1. Root repository keystore: `../../keystore/release.keystore`
2. Directory-level keystore: `release.keystore`

Environment variables for signing:
- `KEYSTORE_PASSWORD`: Keystore access password
- `KEY_ALIAS`: Key alias name
- `KEY_PASSWORD`: Private key password

---

## Roadmap

- **iOS (`mobile/ios`)**: Native Swift 6 and SwiftUI app with SceneKit/Metal 3D globe rendering and CoreLocation observer positioning.
- **Windows (`mobile/windows`)**: Native Windows app using WinUI 3 and Windows App SDK for touch-first handheld and tablet devices.
