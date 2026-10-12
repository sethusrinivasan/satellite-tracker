# Android Store Submission Guide: Google Play Store & Amazon Appstore

This guide provides instructions and pre-filled form values for publishing **Satellite TLE Tracker** to the **Google Play Store** and the **Amazon Appstore**.

---

## 1. Package Artifacts Overview

The automated GitHub Actions workflow (`.github/workflows/android-release.yml`) builds and packages all submission artifacts into a single downloadable release bundle:

| Store | Artifact Required | Format | Purpose |
| :--- | :--- | :--- | :--- |
| **Google Play Store** | Android App Bundle | `app-release.aab` | Play App Signing & dynamic delivery |
| **Google Play Store** | ProGuard Deobfuscation | `mapping.txt` | Stack trace deobfuscation in Play Console |
| **Amazon Appstore** | Standalone Universal APK | `app-release-universal.apk` | Compatible with all Fire OS & Android devices |
| **Both Stores** | Submission Graphics & Metadata | `fastlane/metadata/android/` | Icons, Feature Graphic, Screenshots, Copy |

---

## 2. Google Play Console Submission Steps

### A. Create App & Basic Info
1. Navigate to [Google Play Console](https://play.google.com/console).
2. Click **Create app**:
   - **App name**: `Satellite TLE Tracker & AI` (pre-filled from `fastlane/metadata/android/en-US/title.txt`)
   - **Default language**: English (United States) - `en-US`
   - **App or Game**: App
   - **Free or Paid**: Free
3. Accept Declarations and click **Create app**.

### B. Store Listing Graphics
Upload assets from `fastlane/metadata/android/en-US/images/`:
- **App Icon**: `icon.png` (512x512, 32-bit PNG)
- **Feature Graphic**: `featureGraphic.png` (1024x500 PNG)
- **Phone Screenshots**: `phoneScreenshots/` (5 screenshots in 1080x1920)
- **7-inch Tablet Screenshots**: `sevenInchScreenshots/` (1200x1920)
- **10-inch Tablet Screenshots**: `tenInchScreenshots/` (1600x2560)

### C. Text Descriptions
- **Short Description** (max 80 chars):
  `Real-time 2D/3D satellite tracking, offline SGP4 engine & AI orbit queries.`
- **Full Description** (max 4000 chars):
  Copy directly from `fastlane/metadata/android/en-US/full_description.txt`.

### D. App Content & Declarations
- **Privacy Policy**: Point to your hosted GitHub URL or repo raw markdown:
  `https://github.com/sethusrinivasan/satellite-tracker/blob/main/docs/PRIVACY_POLICY.md`
- **Ads**: Check **No, my app does not contain ads**.
- **App Access**: Check **All functionality is available without special access restrictions**.
- **Content Rating Questionnaire**:
  - Category: Utility / Productivity / Education
  - Violence, Sexual Material, Crude Language, Drugs: **No** to all.
  - Rating received: **PEGI 3 / Everyone (All Ages)**.
- **Target Audience**: Age 13 and up (not aimed primarily at children).
- **Data Safety Declaration**:
  - Does your app collect or share user data? **No** (Location is processed ephemerally strictly on-device for overpass calculations; never transmitted).

### E. App Signing & Release
1. In **Production** (or **Closed testing**):
   - Choose **Google Play App Signing**.
   - Upload `app-release.aab`.
   - Upload `mapping.txt` under **Deobfuscation files** -> **ReTrace mapping file**.
2. Review rollout and submit for review.

---

## 3. Amazon Appstore Submission Steps

### A. Add New App
1. Navigate to [Amazon Developer Console](https://developer.amazon.com/apps-and-games/console).
2. Click **Add New App** -> **Android**.
3. Enter App Title: `Satellite TLE Tracker - Real-Time Orbit & Pass Predictor`.
4. App category: `Education` or `Utilities`.

### B. Upload Binary
1. Under **Upcoming Version** -> **APK Files**:
   - Upload `app-release-universal.apk`.
   - Ensure Amazon Appstore DRM is set to **No** (or default).
   - Target devices: Fire Tablets, Fire TV (if enabled), all non-Amazon Android devices.

### C. Metadata & Assets
Upload from `dist-store/amazon/`:
- **App Icon (512x512)**: `icon_512.png`
- **Small Icon (114x114)**: `icon_114.png`
- **Screenshots**: Upload at least 3 screenshots from `dist-store/amazon/`.
- **Promotional Text**: `Live 2D/3D satellite tracking, overpass predictions, offline SGP4 engine, and AI orbit queries.`
- **Feature Bullets**:
  - `100% On-Device SGP4 Orbit Propagation Engine (zero server latency or dependency)`
  - `Interactive 2D World Map and 3D WebGL Globe with live multi-satellite orbit trails`
  - `60+ preloaded spacecraft with instant CelesTrak ephemeris sync and custom TLE import`
  - `Precise local overpass calculations with sky elevation compass and countdown timers`
  - `Optional Natural Language AI assistant supporting Google Gemini, OpenAI, and Ollama`
- **Keywords**: `satellite, tracker, iss, orbit, sgp4, tle, starlink, nasa, space, passes, astronomy, globe`

### D. Content Rating & Privacy
- Rating: General Audience.
- Privacy Policy: `https://github.com/sethusrinivasan/satellite-tracker/blob/main/docs/PRIVACY_POLICY.md`.
- Submit app for review.

---

## 4. Keystore Generation & Release Signing

For automated release signing in GitHub Actions, create an upload keystore:

```bash
keytool -genkey -v -keystore release.keystore -alias satellitetracker \
  -keyalg RSA -keysize 2048 -validity 10000 \
  -dname "CN=Sethu Srinivasan, O=SatTrack, C=US"
```

Then encode to base64 and set as repository secrets in GitHub:
- `ANDROID_KEYSTORE_BASE64`: `base64 -w 0 release.keystore`
- `ANDROID_KEYSTORE_PASSWORD`: `<your-keystore-password>`
- `ANDROID_KEY_ALIAS`: `satellitetracker`
- `ANDROID_KEY_PASSWORD`: `<your-key-password>`

If secrets are not provided, the CI workflow automatically generates an aligned release signature for dry-run testing and verification.
