import json
import logging
import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from zipfile import ZipFile

from flask import (
    abort,
    flash,
    jsonify,
    make_response,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user, login_required

from app.modules.dataset import dataset_bp
from app.modules.dataset.forms import DataSetForm, EditDataSetForm
from app.modules.dataset.models import DSDownloadRecord
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
)
from app.modules.hubfile.services import HubfileService
from app.modules.zenodo.services import ZenodoService

logger = logging.getLogger(__name__)


dataset_service = DataSetService()
author_service = AuthorService()
dsmetadata_service = DSMetaDataService()
zenodo_service = ZenodoService()
doi_mapping_service = DOIMappingService()
ds_view_record_service = DSViewRecordService()


@dataset_bp.route("/dataset/upload", methods=["GET", "POST"])
@login_required
def create_dataset():
    if current_user.has_role("guest"):
        flash("Guest users cannot create datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))
    form = DataSetForm()
    if request.method == "POST":

        dataset = None

        if not form.validate_on_submit():
            return jsonify({"message": form.errors}), 400

        # Server-side validation: observation essential fields are ALWAYS
        # required
        observation = form.get_observation()

        if not observation:
            msg = "Observation data is required."
            return jsonify({"message": msg}), 400

        # Check required fields
        if not observation.get("object_name") or not observation.get("object_name").strip():
            msg = "Object name is required."
            return jsonify({"message": msg}), 400

        if not observation.get("ra") or not observation.get("ra").strip():
            msg = "RA is required."
            return jsonify({"message": msg}), 400

        if not observation.get("dec") or not observation.get("dec").strip():
            msg = "DEC is required."
            return jsonify({"message": msg}), 400

        if not observation.get("observation_date"):
            msg = "Observation date is required."
            return jsonify({"message": msg}), 400

        try:
            logger.info("Creating dataset...")
            dataset = dataset_service.create_from_form(form=form, current_user=current_user)
            logger.info(f"Created dataset: {dataset}")
            dataset_service.move_hubfiles(dataset)
        except Exception as exc:
            logger.exception(f"Exception while create dataset data in local {exc}")
            # Return a consistent JSON structure with a 'message' key so the frontend
            # can always read `data.message` and display a controlled error
            # message.
            return jsonify({"message": str(exc)}), 400

        data = {}
        try:
            zenodo_response_json = zenodo_service.create_new_deposition(dataset)
            response_data = json.dumps(zenodo_response_json)
            data = json.loads(response_data)
        except Exception as exc:
            data = {}
            zenodo_response_json = {}
            logger.exception(f"Exception while create dataset data in Zenodo {exc}")

        if data.get("conceptrecid"):
            deposition_id = data.get("id")

            # update dataset with deposition id in Zenodo
            dataset_service.update_dsmetadata(dataset.ds_meta_data_id, deposition_id=deposition_id)

            try:
                # iterate for each hubfile (one hubfile = one request to
                # Zenodo)
                for hubfile in dataset.hubfiles:
                    zenodo_service.upload_file(dataset, deposition_id, hubfile)

                # publish deposition
                zenodo_service.publish_deposition(deposition_id)

                # update DOI
                deposition_doi = zenodo_service.get_doi(deposition_id)
                dataset_service.update_dsmetadata(dataset.ds_meta_data_id, dataset_doi=deposition_doi)
            except Exception as e:
                msg = f"it has not been possible upload feature models in Zenodo and update the DOI: {e}"
                return jsonify({"message": msg}), 200

        # Delete temp folder
        file_path = current_user.temp_folder()
        if os.path.exists(file_path) and os.path.isdir(file_path):
            shutil.rmtree(file_path)

        msg = "Everything works!"
        return jsonify({"message": msg}), 200

    return render_template("dataset/upload_dataset.html", form=form)


@dataset_bp.route("/dataset/list", methods=["GET", "POST"])
@login_required
def list_dataset():
    if current_user.has_role("guest"):
        flash("Guest users cannot see their datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))
    if current_user.has_role("curator"):
        dataset = dataset_service.get_all_synchronized_datasets()
        local = dataset_service.get_all_unsynchronized_datasets()
    else:
        dataset = dataset_service.get_synchronized(current_user.id)
        local = dataset_service.get_unsynchronized(current_user.id)
    return render_template(
        "dataset/list_datasets.html",
        datasets=dataset,
        local_datasets=local,
    )


@dataset_bp.route("/dataset/file/upload", methods=["POST"])
@login_required
def upload():
    if current_user.has_role("guest"):
        flash("Guest users cannot upload datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))

    file = request.files["file"]
    temp_folder = current_user.temp_folder()

    if not file or not file.filename.endswith(".json"):
        return jsonify({"message": "No valid file"}), 400

    # create temp folder
    if not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    file_path = os.path.join(temp_folder, file.filename)

    if os.path.exists(file_path):
        # Generate unique filename (by recursion)
        base_name, extension = os.path.splitext(file.filename)
        i = 1
        while os.path.exists(os.path.join(temp_folder, f"{base_name} ({i}){extension}")):
            i += 1
        new_filename = f"{base_name} ({i}){extension}"
        file_path = os.path.join(temp_folder, new_filename)
    else:
        new_filename = file.filename

    try:
        file.save(file_path)
    except Exception as e:
        return jsonify({"message": str(e)}), 500

    return (
        jsonify(
            {
                "message": "JSON uploaded successfully",
                "filename": new_filename,
            }
        ),
        200,
    )


@dataset_bp.route("/dataset/file/delete", methods=["POST"])
def delete():
    if current_user.has_role("guest"):
        flash("Guest users cannot delete datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))

    data = request.get_json()
    filename = data.get("file")
    temp_folder = current_user.temp_folder()
    filepath = os.path.join(temp_folder, filename)
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return jsonify({"message": "File deleted", "filename": filename}), 200
        else:
            return jsonify({"message": "File not found"}), 404
    except Exception as e:
        logger.exception(f"Error deleting temp file: {e}")
        return jsonify({"message": str(e)}), 500


@dataset_bp.route("/dataset/download/<int:dataset_id>", methods=["GET"])
def download_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    # Increment download count
    dataset.download_count += 1
    dataset_service.update(dataset)

    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, f"dataset_{dataset_id}.zip")

    with ZipFile(zip_path, "w") as zipf:
        # Iterar solo sobre los hubfiles del dataset
        for hubfile in dataset.hubfiles:
            file_path = f"uploads/user_{dataset.user_id}/dataset_{dataset.id}/"
            full_path = os.path.join(file_path, hubfile.name)

            if os.path.exists(full_path):
                zipf.write(full_path, arcname=hubfile.name)

    user_cookie = request.cookies.get("download_cookie")
    if not user_cookie:
        user_cookie = str(uuid.uuid4())
        resp = make_response(
            send_from_directory(
                temp_dir,
                f"dataset_{dataset_id}.zip",
                as_attachment=True,
                mimetype="application/zip",
            )
        )
        resp.set_cookie("download_cookie", user_cookie)
    else:
        resp = send_from_directory(
            temp_dir,
            f"dataset_{dataset_id}.zip",
            as_attachment=True,
            mimetype="application/zip",
        )

    # Check if the download record already exists for this cookie
    existing_record = DSDownloadRecord.query.filter_by(
        user_id=current_user.id if current_user.is_authenticated else None,
        dataset_id=dataset_id,
        download_cookie=user_cookie,
    ).first()

    if not existing_record:
        # Record the download in your database
        DSDownloadRecordService().create(
            user_id=current_user.id if current_user.is_authenticated else None,
            dataset_id=dataset_id,
            download_date=datetime.now(timezone.utc),
            download_cookie=user_cookie,
        )

    return resp


@dataset_bp.route("/doi/<path:doi>/", methods=["GET"])
def subdomain_index(doi):

    # Check if the DOI is an old DOI
    new_doi = doi_mapping_service.get_new_doi(doi)
    if new_doi:
        # Redirect to the same path with the new DOI
        return redirect(url_for("dataset.subdomain_index", doi=new_doi), code=302)

    # Try to search the dataset by the provided DOI (which should already be
    # the new one)
    ds_meta_data = dsmetadata_service.filter_by_doi(doi)

    if not ds_meta_data:
        abort(404)

    # Get dataset
    dataset = ds_meta_data.data_set

    # Get recommendations
    recommendations = dataset_service.get_recommendations(dataset.id, limit=5)

    # Save the cookie to the user's browser
    user_cookie = ds_view_record_service.create_cookie(dataset=dataset)

    # Creamos el servicio de hubfile
    hubfile_service = HubfileService()

    resp = make_response(
        render_template(
            "dataset/view_dataset.html",
            dataset=dataset,
            hubfile_service=hubfile_service,
            current_user=current_user,
            recommendations=recommendations,
        )
    )
    resp.set_cookie("view_cookie", user_cookie)
    return resp


@dataset_bp.route("/dataset/unsynchronized/<int:dataset_id>/", methods=["GET"])
@login_required
def get_unsynchronized_dataset(dataset_id):
    if current_user.has_role("guest"):
        flash("Guest users cannot get datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))

    # Get dataset
    dataset = dataset_service.get_unsynchronized_dataset(current_user.id, dataset_id)

    if not dataset:
        abort(404)

    # Get recommendations
    recommendations = dataset_service.get_recommendations(dataset.id, limit=5)

    # Crear servicio de hubfile (igual que en la ruta del DOI)
    hubfile_service = HubfileService()

    return render_template(
        "dataset/view_dataset.html",
        dataset=dataset,
        recommendations=recommendations,
        hubfile_service=hubfile_service,
        current_user=current_user,
    )


@dataset_bp.route("/datasets/import", methods=["GET"])
@login_required
def import_model_page():
    if current_user.has_role("guest"):
        flash("Guest users cannot import datasets. Please register for an account.", "error")
        return redirect(url_for("public.index"))
    return render_template("dataset/import_model.html")


@dataset_bp.route("/datasets/<int:dataset_id>/edit", methods=["GET", "POST"])
@login_required
def edit_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    is_curator = current_user.has_role("curator")

    if not is_curator:
        flash("Only curators can edit datasets.", "error")
        return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset_id))

    form = EditDataSetForm()

    if request.method == "GET":
        form.title.data = dataset.ds_meta_data.title
        form.description.data = dataset.ds_meta_data.description
        form.publication_type.data = dataset.ds_meta_data.publication_type
        form.tags.data = dataset.ds_meta_data.tags

        if dataset.ds_meta_data.observation:
            obs = dataset.ds_meta_data.observation
            form.object_name.data = obs.object_name
            form.ra.data = obs.ra
            form.dec.data = obs.dec
            form.magnitude.data = obs.magnitude
            if obs.observation_date:
                form.observation_date.data = obs.observation_date.strftime("%Y-%m-%dT%H:%M")
            form.filter_used.data = obs.filter_used
            form.notes.data = obs.notes

    if request.method == "POST":
        if form.validate_on_submit():
            try:
                dataset_service.update_from_form(dataset_id, form)
                flash("Dataset updated successfully!", "success")
                return redirect(url_for("dataset.list_dataset"))
            except Exception as exc:
                logger.exception(f"Exception while updating dataset data: {exc}")
                flash(f"Error updating dataset: {exc}", "error")
                return redirect(url_for("dataset.edit_dataset", dataset_id=dataset_id))

    return render_template("dataset/edit_dataset.html", form=form, dataset=dataset)


@dataset_bp.route("/datasets/<int:dataset_id>/delete", methods=["POST"])
@login_required
def delete_dataset(dataset_id):
    dataset = dataset_service.get_or_404(dataset_id)

    is_curator = current_user.has_role("curator")

    if not is_curator:
        flash("Only curators can delete datasets.", "error")
        return redirect(url_for("dataset.list_dataset"))

    try:
        dataset_service.delete(dataset_id)
        flash("Dataset deleted successfully!", "success")
        return redirect(url_for("dataset.list_dataset"))
    except Exception as exc:
        logger.exception(f"Exception while deleting dataset data: {exc}")
        flash(f"Error deleting dataset: {exc}", "error")
        return redirect(url_for("dataset.get_unsynchronized_dataset", dataset_id=dataset_id))
