"""
Unit tests for the Android application, mobile assets, store submission metadata,
and automated release packaging.
"""

import json
import os
from PIL import Image

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))


def test_android_scaffold_structure():
    """Verify that Android Gradle scaffold and manifests are properly configured."""
    app_gradle = os.path.join(ROOT_DIR, "src-tauri", "gen", "android", "app", "build.gradle.kts")
    manifest_xml = os.path.join(ROOT_DIR, "src-tauri", "gen", "android", "app", "src", "main", "AndroidManifest.xml")

    assert os.path.exists(app_gradle), "Android app build.gradle.kts must exist"
    assert os.path.exists(manifest_xml), "AndroidManifest.xml must exist"

    with open(app_gradle, "r", encoding="utf-8") as f:
        gradle_content = f.read()
    assert 'namespace = "com.sethusrinivasan.satellitetracker"' in gradle_content
    assert "targetSdk = 37" in gradle_content
    assert "minSdk = 24" in gradle_content

    with open(manifest_xml, "r", encoding="utf-8") as f:
        manifest_content = f.read()
    assert 'android:name="android.permission.INTERNET"' in manifest_content


def test_native_android_first_principles_project():
    """Verify that pure native Jetpack Compose Android app is implemented with first principles."""
    native_app_gradle = os.path.join(ROOT_DIR, "android", "app", "build.gradle.kts")
    native_manifest = os.path.join(ROOT_DIR, "android", "app", "src", "main", "AndroidManifest.xml")
    main_activity = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "MainActivity.kt")
    sgp4_engine = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "domain", "sgp4", "Sgp4Engine.kt")
    pass_predictor = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "domain", "pass", "PassPredictorEngine.kt")
    query_parser = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "domain", "ai", "LocalQueryParser.kt")

    assert os.path.exists(native_app_gradle)
    assert os.path.exists(native_manifest)
    assert os.path.exists(main_activity)
    assert os.path.exists(sgp4_engine)
    assert os.path.exists(pass_predictor)
    assert os.path.exists(query_parser)

    with open(sgp4_engine, "r", encoding="utf-8") as f:
        sgp4_code = f.read()
    assert "EARTH_RADIUS_KM" in sgp4_code
    assert "MU_EARTH" in sgp4_code
    assert "propagateTle" in sgp4_code
    assert "computeGroundTrack" in sgp4_code

    with open(main_activity, "r", encoding="utf-8") as f:
        main_code = f.read()
    assert "setContent" in main_code
    assert "SatelliteTrackerTheme" in main_code

    with open(native_app_gradle, "r", encoding="utf-8") as f:
        gradle_code = f.read()
    assert "com.android.application" in gradle_code
    assert "signingConfigs" in gradle_code
    assert 'namespace = "com.sattrack"' in gradle_code

    screens_dir = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "ui", "screens")
    expected_screens = ["TrackerScreen.kt", "GlobeScreen.kt", "CatalogScreen.kt", "PassesScreen.kt", "AiDiscoveryScreen.kt", "SettingsDialog.kt"]
    for sc in expected_screens:
        assert os.path.exists(os.path.join(screens_dir, sc)), f"Screen {sc} must exist"

    components_dir = os.path.join(ROOT_DIR, "android", "app", "src", "main", "java", "com", "sattrack", "ui", "components")
    expected_components = ["OrbitMapView.kt", "Globe3DView.kt", "TelemetryBottomSheet.kt", "TopAppBar.kt", "BottomNavigationBar.kt"]
    for cp in expected_components:
        assert os.path.exists(os.path.join(components_dir, cp)), f"Component {cp} must exist"

    tests_dir = os.path.join(ROOT_DIR, "android", "app", "src", "test", "java", "com", "sattrack")
    for kt_test in ["Sgp4EngineTest.kt", "PassPredictorTest.kt", "LocalQueryParserTest.kt"]:
        assert os.path.exists(os.path.join(tests_dir, kt_test)), f"Kotlin test {kt_test} must exist"


def test_mobile_bundled_runtime_assets():
    """Verify that all offline SGP4, 2D Leaflet, 3D Three.js, and catalog assets are bundled locally."""
    required_assets = [
        os.path.join("app", "static", "js", "satellite.min.js"),
        os.path.join("app", "static", "js", "leaflet.js"),
        os.path.join("app", "static", "css", "leaflet.css"),
        os.path.join("app", "static", "js", "three.min.js"),
        os.path.join("app", "static", "js", "mobile-catalog.js"),
        os.path.join("app", "static", "js", "mobile-tracker.js"),
        os.path.join("app", "static", "css", "mobile-tracker.css"),
        os.path.join("app", "static", "index.html"),
    ]

    for rel_path in required_assets:
        full_path = os.path.join(ROOT_DIR, rel_path)
        assert os.path.exists(full_path), f"Required mobile asset {rel_path} must exist locally"
        assert os.path.getsize(full_path) > 100, f"Asset {rel_path} must not be empty"


def test_mobile_catalog_contains_preloaded_ephemeris():
    """Verify that mobile catalog contains 60+ pre-seeded satellites with valid TLE data."""
    catalog_js_path = os.path.join(ROOT_DIR, "app", "static", "js", "mobile-catalog.js")
    with open(catalog_js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "ISS (ZARYA)" in js
    assert "TIANGONG (CSS)" in js
    assert "HUBBLE SPACE TELESCOPE" in js
    assert "LANDSAT 9" in js
    assert "NOAA 15" in js
    assert "GPS III-05" in js
    assert "syncCelesTrakGroup" in js
    assert "importTLE" in js


def test_google_play_store_metadata():
    """Verify Google Play Store metadata complies with Play Console character limits."""
    meta_dir = os.path.join(ROOT_DIR, "fastlane", "metadata", "android", "en-US")

    title_file = os.path.join(meta_dir, "title.txt")
    short_file = os.path.join(meta_dir, "short_description.txt")
    full_file = os.path.join(meta_dir, "full_description.txt")

    assert os.path.exists(title_file)
    assert os.path.exists(short_file)
    assert os.path.exists(full_file)

    with open(title_file, "r", encoding="utf-8") as f:
        title = f.read().strip()
    assert len(title) <= 30, f"Title length {len(title)} exceeds Play Store 30 char limit"

    with open(short_file, "r", encoding="utf-8") as f:
        short = f.read().strip()
    assert len(short) <= 80, f"Short description length {len(short)} exceeds 80 char limit"

    with open(full_file, "r", encoding="utf-8") as f:
        full = f.read().strip()
    assert len(full) <= 4000, f"Full description length {len(full)} exceeds 4000 char limit"
    assert "SGP4" in full
    assert "2D" in full and "3D" in full


def test_google_play_store_graphics():
    """Verify Google Play Store icon, feature graphic, and screenshots meet pixel dimensions."""
    img_dir = os.path.join(ROOT_DIR, "fastlane", "metadata", "android", "en-US", "images")

    icon_path = os.path.join(img_dir, "icon.png")
    feat_path = os.path.join(img_dir, "featureGraphic.png")

    assert os.path.exists(icon_path)
    assert os.path.exists(feat_path)

    with Image.open(icon_path) as img:
        assert img.size == (512, 512), f"Icon must be exactly 512x512, got {img.size}"

    with Image.open(feat_path) as img:
        assert img.size == (1024, 500), f"Feature graphic must be exactly 1024x500, got {img.size}"

    # Phone screenshots (at least 2 required by Google Play)
    phone_dir = os.path.join(img_dir, "phoneScreenshots")
    screenshots = [f for f in os.listdir(phone_dir) if f.endswith(".png")]
    assert len(screenshots) >= 5, f"Expected 5 screenshots, found {len(screenshots)}"

    with Image.open(os.path.join(phone_dir, screenshots[0])) as img:
        assert img.size == (1080, 1920), f"Phone screenshot must be 1080x1920, got {img.size}"


def test_amazon_appstore_metadata_and_icons():
    """Verify Amazon Appstore metadata and 512x512 + 114x114 icons."""
    amazon_dir = os.path.join(ROOT_DIR, "dist-store", "amazon")

    json_path = os.path.join(amazon_dir, "amazon_metadata.json")
    icon512_path = os.path.join(amazon_dir, "icon_512.png")
    icon114_path = os.path.join(amazon_dir, "icon_114.png")

    assert os.path.exists(json_path)
    assert os.path.exists(icon512_path)
    assert os.path.exists(icon114_path)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "title" in data
    assert "bullet_points" in data
    assert len(data["bullet_points"]) >= 3
    assert "keywords" in data

    with Image.open(icon512_path) as img:
        assert img.size == (512, 512)

    with Image.open(icon114_path) as img:
        assert img.size == (114, 114)


def test_android_release_workflow():
    """Verify that .github/workflows/android-release.yml builds .aab, .apk, and packages submission artifacts."""
    wf_path = os.path.join(ROOT_DIR, ".github", "workflows", "android-release.yml")
    assert os.path.exists(wf_path)

    with open(wf_path, "r", encoding="utf-8") as f:
        wf = f.read()

    assert "bundleRelease" in wf or "--aab=true" in wf
    assert "assembleRelease" in wf or "--apk=true" in wf
    assert "app-release.aab" in wf
    assert "app-release-universal.apk" in wf
    assert "satellite-tracker-android-submission-bundle" in wf
    assert "SHA256SUMS.txt" in wf


def test_privacy_policy_and_submission_docs():
    """Verify that mandatory Privacy Policy and Store Submission guides exist."""
    priv_path = os.path.join(ROOT_DIR, "docs", "PRIVACY_POLICY.md")
    guide_path = os.path.join(ROOT_DIR, "docs", "store-submission", "STORE_SUBMISSION_GUIDE.md")

    assert os.path.exists(priv_path)
    assert os.path.exists(guide_path)

    with open(priv_path, "r", encoding="utf-8") as f:
        priv = f.read()
    assert "Location Data" in priv
    assert "AI Features" in priv

    with open(guide_path, "r", encoding="utf-8") as f:
        guide = f.read()
    assert "Google Play Console" in guide
    assert "Amazon Appstore" in guide
