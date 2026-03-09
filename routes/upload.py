import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename
from services.processor import process_upload

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls"}


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route("/upload", methods=["GET"])
def upload():
    return render_template("upload.html")


@upload_bp.route("/upload", methods=["POST"])
def process():
    if "file" not in request.files:
        flash("Nenhum arquivo enviado.", "error")
        return redirect(url_for("upload.upload"))

    file = request.files["file"]

    if file.filename == "":
        flash("Nenhum arquivo selecionado.", "error")
        return redirect(url_for("upload.upload"))

    if not _allowed_file(file.filename):
        flash("Formato inválido. Use CSV, XLS ou XLSX.", "error")
        return redirect(url_for("upload.upload"))

    filename = secure_filename(file.filename)
    filepath = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
    file.save(filepath)

    result = process_upload(filepath)

    # Clean up temp file
    try:
        os.remove(filepath)
    except OSError:
        pass

    if result["errors"] and result["processed"] == 0:
        for err in result["errors"]:
            flash(err, "error")
        return redirect(url_for("upload.upload"))

    flash(
        f"{result['processed']} resultado(s) processado(s) com sucesso!",
        "success",
    )
    if result["errors"]:
        for err in result["errors"]:
            flash(err, "warning")

    return redirect(url_for("dashboard.index"))
