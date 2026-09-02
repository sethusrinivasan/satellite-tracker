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
    # If credentials not configured, show a helpful error page instead of
    # crashing with a cryptic OAuth error.
    if not current_app.config.get("GOOGLE_CLIENT_ID"):
        return render_template("auth_error.html",
                               title="OAuth Not Configured",
                               message=(
                                   "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment "
                                   "variables are not set. "
                                   "Add them to your .env file and restart the server."
                               )), 503

    redirect_uri = url_for("auth.callback", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


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
