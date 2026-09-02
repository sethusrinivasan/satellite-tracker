import os
from flask import Blueprint, request, render_template, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename
from app.services.tle_parser import parse_tle_file
from app.services.db_service import upsert_tle_records
from app.models import Upload

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"txt", "tle", "dat"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/", methods=["GET"])
def index():
    return redirect(url_for("report.report"))


@upload_bp.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        flash("No file part in the request.", "error")
        return redirect(url_for("upload.index"))

    file = request.files["file"]
    if file.filename == "":
        flash("No file selected.", "error")
        return redirect(url_for("upload.index"))

    if not allowed_file(file.filename):
        flash("Invalid file type. Please upload a .txt, .tle, or .dat file.", "error")
        return redirect(url_for("upload.index"))

    filename = secure_filename(file.filename)
    content = file.read().decode("utf-8", errors="replace")

    parsed = parse_tle_file(content)
    if not parsed:
        flash("No valid TLE records found in the uploaded file.", "warning")
        return redirect(url_for("upload.index"))

    summary = upsert_tle_records(parsed, filename)
    return render_template("upload_result.html", summary=summary)
