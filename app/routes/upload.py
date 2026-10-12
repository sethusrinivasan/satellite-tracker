import ipaddress
import logging
import os
import socket
import urllib.parse
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, url_for
import requests
from werkzeug.utils import secure_filename

from app.models import Upload
from app.services.db_service import upsert_tle_records
from app.services.tle_parser import parse_tle_file

logger = logging.getLogger(__name__)

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"txt", "tle", "dat"}
DEFAULT_CELESTRAK_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"
ALLOWED_TLE_HOSTS = {
    "celestrak.org",
    "celestrak.com",
    "www.celestrak.org",
    "www.celestrak.com",
    "space-track.org",
    "www.space-track.org",
    "example.com",
}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def is_safe_url(url: str) -> bool:
    """Validate that URL uses http/https, targets trusted TLE hosts, and prevents SSRF."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").lower().strip()
        if not hostname:
            return False
        if (
            hostname not in ALLOWED_TLE_HOSTS
            and not hostname.endswith(".celestrak.org")
            and not hostname.endswith(".celestrak.com")
        ):
            return False
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "169.254.169.254"):
            return False
        try:
            addr = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(addr)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
                return False
        except (socket.gaierror, ValueError):
            return False
        return True
    except Exception:
        return False


def derive_filename_from_url(url: str) -> str:
    """Derive a friendly audit filename from the TLE query parameters or URL path."""
    try:
        parsed = urllib.parse.urlparse(url)
        qs = urllib.parse.parse_qs(parsed.query)
        if "GROUP" in qs and qs["GROUP"]:
            return f"celestrak_{secure_filename(qs['GROUP'][0].lower())}.tle"
        elif "CATNR" in qs and qs["CATNR"]:
            return f"celestrak_{secure_filename(qs['CATNR'][0])}.tle"
        path = parsed.path.strip("/").split("/")[-1]
        if path and "." in path:
            return secure_filename(path)
    except Exception:
        pass
    return "celestrak_active.tle"


def fetch_tle_from_url(url: str, timeout: int = 30) -> tuple[str | None, str | None, str | None]:
    """
    Fetch TLE content from a remote URL with CelesTrak rate-policy handling and local caching.
    Returns: (content, warning_or_info_msg, error_msg)
    """
    if not is_safe_url(url):
        return None, None, "Invalid or prohibited URL. Only public http/https URLs are permitted."

    filename = derive_filename_from_url(url)
    cache_dir = os.path.join(current_app.instance_path, "celestrak_cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, filename)

    # Fallback pre-cached snapshot in data/ directory
    repo_data_dir = os.path.join(current_app.root_path, "..", "data")
    fallback_file = os.path.join(repo_data_dir, "celestrak_active_cache.tle")

    headers = {
        "User-Agent": "SatTrack/1.0 (Satellite TLE Explorer; +https://github.com/sethusrinivasan/satellite-tracker)",
        "Accept": "text/plain, */*",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
    except requests.exceptions.RequestException as exc:
        logger.warning("[upload] Failed to fetch TLE from %s: %s", url, exc)
        # Check if we have cached copy to recover gracefully
        target_file = cache_file if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0 else (
            fallback_file if os.path.isfile(fallback_file) and os.path.getsize(fallback_file) > 0 else None
        )
        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    cached_data = f.read()
                return cached_data, "Remote request failed; imported from recent local snapshot.", None
            except OSError:
                pass
        return None, None, "Failed to connect to remote URL. Please verify your connection or try again later."

    if resp.status_code == 200:
        content = resp.text
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError:
            pass
        return content, None, None

    # Handle CelesTrak 403 / 429 rate policies (e.g. 2-hour interval restriction per IP)
    resp_text = resp.text.strip()
    if resp.status_code in (403, 429) and "has not updated since your last successful download" in resp_text:
        target_file = cache_file if os.path.isfile(cache_file) and os.path.getsize(cache_file) > 0 else (
            fallback_file if os.path.isfile(fallback_file) and os.path.getsize(fallback_file) > 0 else None
        )
        if target_file:
            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    cached_data = f.read()
                return (
                    cached_data,
                    "CelesTrak rate notice: Data is updated once every 2 hours. Ingested from recent local CelesTrak snapshot.",
                    None,
                )
            except OSError:
                pass
        return None, None, "CelesTrak Notice: Data is updated once every 2 hours."

    return None, None, f"Remote server returned HTTP {resp.status_code}."


@upload_bp.route("/", methods=["GET"])
def index():
    return redirect(url_for("report.report"))


@upload_bp.route("/import-url", methods=["POST"])
def import_from_url():
    is_json_req = (
        request.is_json
        or request.headers.get("Accept") == "application/json"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or (request.form.get("format") == "json")
    )
    url = (
        request.json.get("url")
        if request.is_json
        else (request.form.get("url") or "")
    ).strip()
    if not url:
        url = DEFAULT_CELESTRAK_URL

    content, notice, err = fetch_tle_from_url(url)
    if err:
        if is_json_req:
            return jsonify({"success": False, "error": err}), 400
        flash(err, "error")
        return redirect(url_for("upload.upload_file"))

    parsed = parse_tle_file(content or "")
    if not parsed:
        if is_json_req:
            return jsonify({"success": False, "error": "No valid TLE records found at the specified URL."}), 400
        flash("No valid TLE records found at the specified URL.", "warning")
        return redirect(url_for("upload.upload_file"))

    filename = derive_filename_from_url(url)
    label = f"CelesTrak Import ({filename})"
    summary = upsert_tle_records(parsed, filename, source="celestrak_url", label=label)

    if is_json_req:
        return jsonify({
            "success": True,
            "notice": notice,
            "filename": filename,
            "label": label,
            "parsed_count": len(parsed),
            "created_count": summary.get("new_satellites", 0),
            "updated_count": summary.get("updated_satellites", 0),
            "duplicate_count": summary.get("duplicate_epochs", 0),
            "total_count": summary.get("total_in_file", 0),
            "redirect_url": url_for("report.report"),
        })

    if notice:
        flash(notice, "info")

    return render_template("upload_result.html", summary=summary)


@upload_bp.route("/upload", methods=["GET", "POST"])
def upload_file():
    if request.method in ("GET", "HEAD"):
        recent_uploads = (
            Upload.query.order_by(Upload.upload_time.desc()).limit(10).all()
        )
        return render_template(
            "upload.html",
            recent_uploads=recent_uploads,
            default_url=DEFAULT_CELESTRAK_URL,
        )

    # If submitted via URL form to /upload
    if request.form.get("url"):
        return import_from_url()

    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("upload.upload_file"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("upload.upload_file"))

    if not allowed_file(file.filename):
        flash("Invalid file type. Please upload a .txt, .tle, or .dat file.", "error")
        return redirect(url_for("upload.upload_file"))

    filename = secure_filename(file.filename)
    content = file.read().decode("utf-8", errors="replace")

    parsed = parse_tle_file(content)
    if not parsed:
        flash("No valid TLE records found in the uploaded file.", "warning")
        return redirect(url_for("upload.upload_file"))

    summary = upsert_tle_records(parsed, filename)
    return render_template("upload_result.html", summary=summary)
