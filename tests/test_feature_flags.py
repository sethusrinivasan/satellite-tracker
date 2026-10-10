import os
import shutil
import tempfile
import unittest

from app import create_app, db
from app.services.feature_flags import get_feature_flags


class FeatureFlagTestCase(unittest.TestCase):
    def setUp(self):
        self.runtime_dir = tempfile.mkdtemp(prefix="satellite-tracker-tests-")
        self.previous_vercel = os.environ.get("VERCEL")
        os.environ["VERCEL"] = "1"
        os.environ["SATELLITE_RUNTIME_DIR"] = self.runtime_dir

        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret"
            DATASTORE_CONFIGURED = True
            DATASTORE_ENGINE = "sqlite"
            SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.runtime_dir}/test.db"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = f"{self.runtime_dir}/uploads"
            GOOGLE_CLIENT_ID = ""
            GOOGLE_CLIENT_SECRET = ""
            ADMIN_ALLOWED_EMAILS = "test@example.com"

        self.app = create_app(TestConfig)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        if self.previous_vercel is None:
            os.environ.pop("VERCEL", None)
        else:
            os.environ["VERCEL"] = self.previous_vercel
        os.environ.pop("SATELLITE_RUNTIME_DIR", None)
        shutil.rmtree(self.runtime_dir, ignore_errors=True)

    def sign_in_as_admin(self):
        with self.client.session_transaction() as session:
            session["admin_user"] = {"email": "test@example.com"}

    def test_vercel_defaults_disable_server_features(self):
        with self.app.app_context():
            self.assertEqual(
                get_feature_flags(),
                {
                    "offline_ai_search": False,
                    "ai_model_management": False,
                    "system_telemetry": False,
                },
            )

        report = self.client.get("/report")
        self.assertEqual(report.status_code, 200)
        self.assertNotIn(b'id="tab-ai-btn"', report.data)
        self.assertNotIn(b'id="ai-search-container"', report.data)

    def test_disabled_endpoints_are_guarded(self):
        ai_response = self.client.post(
            "/api/natural-query", json={"prompt": "show satellites"}
        )
        self.assertEqual(ai_response.status_code, 503)

        self.sign_in_as_admin()
        model_response = self.client.get("/admin/model-status")
        self.assertEqual(model_response.status_code, 503)

    def test_admin_can_enable_flags_for_testing(self):
        self.sign_in_as_admin()
        response = self.client.post(
            "/admin/feature-flags",
            data={
                "offline_ai_search": "on",
                "ai_model_management": "on",
                "system_telemetry": "on",
            },
        )
        self.assertEqual(response.status_code, 302)

        with self.app.app_context():
            self.assertTrue(all(get_feature_flags().values()))

        report = self.client.get("/report")
        self.assertIn(b'id="tab-ai-btn"', report.data)
        model_response = self.client.get("/admin/model-status")
        self.assertEqual(model_response.status_code, 200)


    def test_vercel_config_structure(self):
        import json

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vercel_json_path = os.path.join(repo_root, "vercel.json")
        self.assertTrue(os.path.exists(vercel_json_path))
        with open(vercel_json_path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
        self.assertIn(cfg.get("version"), (2, None))
        self.assertIn("api/index.py", cfg.get("functions", {}))
        rewrites = cfg.get("rewrites", [])
        self.assertTrue(any(r.get("destination", "").startswith("/api/index") for r in rewrites))

    def test_api_index_entrypoint(self):
        from api.index import app as vercel_app

        client = vercel_app.test_client()
        health = client.get("/health")
        self.assertEqual(health.status_code, 200)

    def test_runtime_dir_resolutions(self):
        from app.services.datastore import default_sqlite_path
        from app.services import overlay_cache

        self.assertTrue(default_sqlite_path().startswith(self.runtime_dir))
        prev_overlay = os.environ.pop("OVERLAY_CACHE_DIR", None)
        try:
            self.assertTrue(str(overlay_cache.cache_dir()).startswith(self.runtime_dir))
        finally:
            if prev_overlay:
                os.environ["OVERLAY_CACHE_DIR"] = prev_overlay


if __name__ == "__main__":
    unittest.main()
