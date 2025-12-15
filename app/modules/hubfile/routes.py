import io
import os
import uuid
import zipfile
from datetime import datetime, timezone

# Note: FlamaPy removed — export will return original files only
from flask import (
    current_app,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app import db
from app.modules.hubfile import hubfile_bp
from app.modules.hubfile.models import HubfileDownloadRecord, HubfileViewRecord
from app.modules.hubfile.services import HubfileDownloadRecordService, HubfileService
from app.modules.jsonChecker import validate_json_file


@hubfile_bp.route("/file/download/<int:file_id>", methods=["GET"])
def download_file(file_id):
    file = HubfileService().get_or_404(file_id)
    filename = file.name
    dataset = file.get_dataset()
    directory_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"
    parent_directory_path = os.path.dirname(current_app.root_path)
    file_path = os.path.join(parent_directory_path, directory_path)

    # Get the cookie from the request or generate a new one if it does not
    # exist
    user_cookie = request.cookies.get("file_download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())

    # Check if the download record already exists for this cookie
    existing_record = HubfileDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None, file_id=file_id, download_cookie=user_cookie
    ).first()

    if not existing_record:
        # Record the download in your database
        HubfileDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            file_id=file_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

    # Save the cookie to the user's browser
    resp = make_response(send_from_directory(directory=file_path, path=filename, as_attachment=True))
    resp.set_cookie("file_download_cookie", user_cookie)

    return resp


@hubfile_bp.route("/file/check_json/<int:file_id>", methods=["GET"])
def check_json(file_id):
    """Validate a saved hubfile as JSON and return validation result."""
    try:
        hubfile = HubfileService().get_or_404(file_id)
        path = hubfile.get_path()
        if not path or not os.path.exists(path):
            return jsonify({"error": "File not found"}), 404

        res = validate_json_file(path)
        # If parse error or not JSON -> 400
        if not res.get("is_json"):
            return jsonify({"is_json": False, "valid": False, "errors": res.get("errors", [])}), 400

        # If parsed but invalid structure -> 400 with errors
        if not res.get("valid"):
            return jsonify({"is_json": True, "valid": False, "errors": res.get("errors", [])}), 400

        # Valid JSON and structure
        return jsonify({"is_json": True, "valid": True, "errors": []}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@hubfile_bp.route("/file/view/<int:file_id>", methods=["GET"])
def view_file(file_id):
    file = HubfileService().get_or_404(file_id)
    filename = file.name
    dataset = file.get_dataset()
    directory_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"
    parent_directory_path = os.path.dirname(current_app.root_path)
    file_path = os.path.join(parent_directory_path, directory_path, filename)

    try:
        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # If the file is a JSON, validate structure and include results
            validation = None
            if filename.lower().endswith(".json"):
                try:
                    validation = validate_json_file(file_path)
                except Exception as e:
                    validation = {"is_json": False, "valid": False, "errors": [str(e)], "data": None}

            user_cookie = request.cookies.get("view_cookie")
            if not user_cookie:
                user_cookie = str(uuid.uuid4())

            # Check if the view record already exists for this cookie
            existing_record = HubfileViewRecord.query.filter_by(
                user_id=current_user.id if current_user.is_authenticated else None,
                file_id=file_id,
                view_cookie=user_cookie,
            ).first()

            if not existing_record:
                # Register file view
                new_view_record = HubfileViewRecord(
                    user_id=current_user.id if current_user.is_authenticated else None,
                    file_id=file_id,
                    view_date=datetime.now(),
                    view_cookie=user_cookie,
                )
                db.session.add(new_view_record)
                db.session.commit()

            # Prepare response
            payload = {"success": True, "content": content}
            if validation is not None:
                payload["json_is_json"] = validation.get("is_json")
                payload["json_valid"] = validation.get("valid")
                payload["json_errors"] = validation.get("errors")

            response = jsonify(payload)
            if not request.cookies.get("view_cookie"):
                response = make_response(response)
                response.set_cookie("view_cookie", user_cookie, max_age=60 * 60 * 24 * 365 * 2)

            return response
        else:
            return jsonify({"success": False, "error": "File not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Endpoint para guardar un archivo en el carrito
@hubfile_bp.route("/file/save/<int:file_id>", methods=["POST"])
def save_file(file_id):
    # First ensure the user is authenticated before asking about roles.
    if not current_user.is_authenticated:
        # Keep behavior consistent with `unsave_file` which returns this error
        # string
        return jsonify({"success": False, "error": "not_authenticated"})

    # Guard the role check in case user object does not implement has_role
    has_role = getattr(current_user, "has_role", lambda role: False)
    if has_role("guest"):
        return jsonify({"success": False, "error": "You must be logged in as a user to save files."})
    try:
        HubfileService().add_to_user_saved(file_id, current_user.id)
        return jsonify({"success": True, "message": "File saved successfully", "saved": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Endpoint para eliminar un archivo del carrito
@hubfile_bp.route("/file/unsave/<int:file_id>", methods=["POST"])
def unsave_file(file_id):
    if not current_user.is_authenticated:
        return jsonify({"success": False, "error": "not_authenticated"})
    try:
        HubfileService().remove_from_user_saved(file_id, current_user.id)
        return jsonify({"success": True, "message": "File removed successfully", "removed": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# Endpoint para obtener la lista de archivos guardados por el usuario
@hubfile_bp.route("/file/saved", methods=["GET"])
def get_saved_files():
    try:
        saved_files = HubfileService().get_saved_files_for_user(current_user.id)
        files_list = [file.to_dict() for file in saved_files]
        return jsonify({"success": True, "files": files_list})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hubfile_bp.route("/file/saved/view", methods=["GET"])
@login_required
def view_saved_files():
    if current_user.has_role("guest"):
        flash("Guest users cannot see saved datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))

    hubfile_service = HubfileService()
    saved_files = hubfile_service.get_saved_files_for_user(current_user.id)

    files_data = []
    for f in saved_files:
        files_data.append(
            {
                "id": f.id,
                "name": f.name,
                "dataset_title": f.get_dataset().ds_meta_data.title if f.get_dataset() else "",
                "saved": hubfile_service.is_saved_by_user(f.id, current_user.id),
            }
        )

    return render_template("hubfile/saved_files.html", files_data=files_data)


# Endpoint para descargar todos los archivos guardados como un ZIP
@hubfile_bp.route("/file/saved/download_all", methods=["GET"])
@login_required
def download_all_saved():
    # Obtener el formato solicitado (uvl, glencoe, cnf, splot)
    export_format = request.args.get("export_format", "uvl").lower()

    saved_files = HubfileService().get_saved_files_for_user(current_user.id)

    if not saved_files:
        return "No saved files to download.", 404

    # Export: write original files into the ZIP. Conversions were removed with
    # FlamaPy.

    # Cookie para registro de descargas (se usará la misma para todos los
    # ficheros del ZIP)
    user_cookie = request.cookies.get("file_download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())

    # Creamos un ZIP en memoria
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for file in saved_files:
            try:
                dataset = file.get_dataset()
                # Construimos la ruta al archivo original
                directory_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"
                parent_directory_path = os.path.dirname(current_app.root_path)
                original_path = os.path.join(parent_directory_path, directory_path, file.name)

                # Add the original file into the ZIP if it exists
                if os.path.exists(original_path):
                    zipf.write(original_path, arcname=file.name)
                else:
                    print(f"Warning: File not found {original_path}")

                # Creación del registro de descarga (opcional)
                existing_record = HubfileDownloadRecord.query.filter_by(
                    user_id=current_user.id, file_id=file.id, download_cookie=user_cookie
                ).first()

                if not existing_record:
                    HubfileDownloadRecordService().create(
                        user_id=current_user.id,
                        file_id=file.id,
                        download_date=datetime.now(timezone.utc),
                        download_cookie=user_cookie,
                    )

            except Exception as e:
                print(f"Error processing file {file.id} for export: {e}")
                continue

    zip_buffer.seek(0)
    resp = make_response(
        send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"saved_files_JSON.zip",
        )
    )
    resp.set_cookie("file_download_cookie", user_cookie)
    return resp
