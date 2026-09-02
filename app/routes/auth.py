"""
Auth Blueprint — Google OAuth2 login/logout for the Admin panel.

Flow:
  GET  /auth/login          → redirect to Google consent screen
  GET  /auth/callback       → handle Google redirect, set session
  GET  /auth/logout         → clear session, redirect home
  GET  /auth/me             → JSON: current user info (used by frontend)

Protected pages use the @admin_required decorator defined here.
"""

from functools import wraps
from flask import (
    Blueprint, current_app, redirect, request,
    session, url_for, flash, jsonify, render_template,
)
from authlib.integrations.flask_client import OAuth

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Module-level OAuth instance – registered with the app in create_app()
oauth = OAuth()


def init_oauth(app):
    """Call once from create_app() to attach the Google provider."""
    oauth.init_app(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=app.config["GOOGLE_CLIENT_ID"],
        client_secret=app.config["GOOGLE_CLIENT_SECRET"],
        client_kwargs={
            "scope": "openid email profile",
            # Prompt for account selection every time so users can switch accounts
            "prompt": "select_account",
        },
    )


# ── Helpers ──────────────────────────────────────────────────────────────────

def is_local_dev():
    """Return True if running in local development or Docker development mode."""
    import os
    env = os.environ.get("FLASK_ENV") or os.environ.get("ENV") or ""
    host = request.host.split(":")[0] if request else ""
    is_docker = os.path.exists('/.dockerenv') or os.environ.get("RUNNING_IN_DOCKER") == "true" or os.environ.get("CONTAINER_ENV") == "docker"
    return (
        current_app.debug
        or is_docker
        or env.lower() in ("development", "dev", "local")
        or host in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal")
    )


def is_valid_google_client_id(client_id):
    """Return True if client_id is set and is not a dummy placeholder from .env.example."""
    if not client_id or not isinstance(client_id, str):
        return False
    cid = client_id.strip().lower()
    placeholders = ["your-google", "your-client", "your_google", "change-me", "example.com"]
    return not any(p in cid for p in placeholders)


def _allowed_emails(app=None):
    """Return a set of lowercase allowed emails, or empty set (= allow all)."""
    cfg = (app or current_app)
    raw = cfg.config.get("ADMIN_ALLOWED_EMAILS", "")
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


def current_user():
    """Return the logged-in user dict from the session, or None."""
    return session.get("admin_user")


def admin_required(f):
    """
    Decorator that protects a view to authenticated admins only.
    Redirects to /auth/login if not authenticated.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = current_user()
        if not user:
            flash("Please sign in with Google to access the Admin panel.", "warning")
            session["next_url"] = request.url
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Routes ───────────────────────────────────────────────────────────────────

@auth_bp.route("/login")
def login():
    local_dev = is_local_dev()
    client_id = current_app.config.get("GOOGLE_CLIENT_ID")
    
    # If credentials are not configured or are placeholder strings, show auth_error page
    if not is_valid_google_client_id(client_id):
        return render_template("auth_error.html",
                               title="OAuth Not Configured",
                               message=(
                                   "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment "
                                   "variables are not set or contain dummy placeholders. "
                                   "To enable Google OAuth2 authentication, obtain valid credentials "
                                   "from Google Cloud Console and add them to your .env file."
                               ),
                               is_local_dev=local_dev), 503

    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route("/dev-bypass", methods=["GET", "POST"])
def dev_bypass():
    """
    Dev-only route allowing one-click Admin access without Google OAuth when running locally.
    Strictly disabled in production mode.
    """
    if not is_local_dev():
        flash("Dev bypass is strictly disabled in production environments.", "error")
        return redirect(url_for("upload.index")), 403

    session.permanent = True
    session["admin_user"] = {
        "email": "dev-admin@localhost",
        "name": "Local Dev Admin (Bypass)",
        "picture": "",
        "sub": "dev-local-001",
        "is_dev_bypass": True,
    }
    flash("⚠️ Logged in to Admin Panel via Local Dev Bypass (Development Mode Only).", "warning")
    next_url = session.pop("next_url", None)
    return redirect(next_url or url_for("admin.index"))


@auth_bp.route("/callback")
def callback():
    try:
        token = oauth.google.authorize_access_token()
    except Exception as exc:
        current_app.logger.warning("OAuth callback error: %s", exc)
        flash("Google sign-in failed. Please try again.", "error")
        return redirect(url_for("upload.index"))

    user_info = token.get("userinfo") or oauth.google.userinfo()

    email = (user_info.get("email") or "").lower()
    allowed = _allowed_emails()
    if allowed and email not in allowed:
        flash(
            f"Access denied: {email} is not authorised to access the Admin panel.",
            "error",
        )
        return redirect(url_for("upload.index"))

    # Store minimal user info in the server-side session (signed cookie)
    session.permanent = True
    session["admin_user"] = {
        "email":   email,
        "name":    user_info.get("name", email),
        "picture": user_info.get("picture", ""),
        "sub":     user_info.get("sub", ""),
    }

    next_url = session.pop("next_url", None)
    flash(f"Signed in as {email}", "success")
    return redirect(next_url or url_for("admin.index"))


@auth_bp.route("/logout")
def logout():
    user = session.pop("admin_user", None)
    name = (user or {}).get("email", "")
    if name:
        flash(f"Signed out from {name}.", "info")
    return redirect(url_for("upload.index"))


@auth_bp.route("/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": user})
