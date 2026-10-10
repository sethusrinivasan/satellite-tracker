import unittest

from app import create_app, db
from app.services.ai_prompt_service import (
    DEFAULT_AI_SYSTEM_PROMPT,
    get_ai_system_prompt,
    set_ai_system_prompt,
    reset_ai_system_prompt,
    is_custom_prompt_active,
)


class TestAiPromptService(unittest.TestCase):
    def setUp(self):
        class TestConfig:
            TESTING = True
            SECRET_KEY = "test-secret"
            DATASTORE_CONFIGURED = True
            DATASTORE_ENGINE = "sqlite"
            SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            UPLOAD_FOLDER = "/tmp/sat_test_uploads"
            GOOGLE_CLIENT_ID = ""
            GOOGLE_CLIENT_SECRET = ""
            ADMIN_ALLOWED_EMAILS = "admin@example.com"

        self.app = create_app(TestConfig)
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def sign_in_as_admin(self):
        with self.client.session_transaction() as session:
            session["admin_user"] = {"email": "admin@example.com"}

    def test_default_prompt_active_initially(self):
        with self.app.app_context():
            self.assertFalse(is_custom_prompt_active())
            self.assertEqual(get_ai_system_prompt(), DEFAULT_AI_SYSTEM_PROMPT.strip())

    def test_set_and_reset_custom_prompt(self):
        with self.app.app_context():
            custom = "Custom system prompt for testing."
            set_ai_system_prompt(custom)
            self.assertTrue(is_custom_prompt_active())
            self.assertEqual(get_ai_system_prompt(), custom)

            reset_ai_system_prompt()
            self.assertFalse(is_custom_prompt_active())
            self.assertEqual(get_ai_system_prompt(), DEFAULT_AI_SYSTEM_PROMPT.strip())

    def test_admin_routes_manage_prompt(self):
        self.sign_in_as_admin()

        # Admin page displays prompt
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"AI System Prompt & Few-Shot Examples", resp.data)

        # Update prompt via POST
        update_resp = self.client.post(
            "/admin/system-prompt",
            data={"system_prompt": "Updated prompt via admin panel"},
            follow_redirects=True,
        )
        self.assertEqual(update_resp.status_code, 200)
        with self.app.app_context():
            self.assertEqual(get_ai_system_prompt(), "Updated prompt via admin panel")
            self.assertTrue(is_custom_prompt_active())

        # Reset prompt via POST
        reset_resp = self.client.post(
            "/admin/system-prompt/reset",
            follow_redirects=True,
        )
        self.assertEqual(reset_resp.status_code, 200)
        with self.app.app_context():
            self.assertFalse(is_custom_prompt_active())
            self.assertEqual(get_ai_system_prompt(), DEFAULT_AI_SYSTEM_PROMPT.strip())

    def test_unauthorized_user_cannot_update_prompt(self):
        resp = self.client.post(
            "/admin/system-prompt",
            data={"system_prompt": "Malicious override"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/auth/login", resp.headers.get("Location", ""))


if __name__ == "__main__":
    unittest.main()
