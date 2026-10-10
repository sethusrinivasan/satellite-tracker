import os
import sys

# Ensure repository root is on sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from run import app  # noqa: E402


class VercelPathFixMiddleware:
    """WSGI middleware to preserve the original requested URL path when running under Vercel rewrites."""

    def __init__(self, wsgi_app):
        self.wsgi_app = wsgi_app

    def __call__(self, environ, start_response):
        path_info = environ.get("PATH_INFO", "")
        if path_info in ("/api/index", "/api/index.py", "/api"):
            matched = (
                environ.get("HTTP_X_FORWARDED_URI")
                or environ.get("HTTP_X_ORIGINAL_URI")
                or environ.get("REQUEST_URI")
                or environ.get("HTTP_X_MATCHED_PATH")
            )
            if matched:
                path = matched.split("?", 1)[0]
                if path:
                    environ["PATH_INFO"] = path
            else:
                environ["PATH_INFO"] = "/"
        return self.wsgi_app(environ, start_response)


app.wsgi_app = VercelPathFixMiddleware(app.wsgi_app)

