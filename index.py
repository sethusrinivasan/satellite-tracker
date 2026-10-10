import os
import sys

# Ensure repository root is on sys.path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from run import app  # noqa: E402

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() in {"1", "true", "yes", "on"}
    app.run(debug=debug_mode, host="0.0.0.0", port=5000)
