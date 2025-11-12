import json
from datetime import datetime
from flask import request, jsonify, render_template, url_for
from flask_login import login_required, current_user

from app import db
from app.modules.dataset.services import DataSetService
from .models import AstronomyObservation, AstronomyAttachment
from . import astronomy_bp

@astronomy_bp.route("/astronomy/create", methods=["GET"])
@login_required
def create_astronomy_dataset_form():
    # Plantilla simple con un textarea para pegar el JSON (puedes crearla en templates/astronomy/create.html)
    return render_template("astronomy/create.html")

def _create_dataset_from_dataset_info(dataset_info, current_user):
    dss = DataSetService()
    dataset = dss.create_from_dict(dataset_info=dataset_info, current_user=current_user)
    return dataset

@astronomy_bp.route("/api/astronomy/upload-json", methods=["POST"])
@login_required
def upload_astronomy_json():
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception as exc:
        return jsonify({"error": "Invalid JSON", "details": str(exc)}), 400

    if not isinstance(payload, dict):
        return jsonify({"error": "JSON must be an object"}), 400

    dataset_info = payload.get("dataset_info")
    observations = payload.get("observations", [])
    attachments = payload.get("attachments", [])

    if not dataset_info:
        return jsonify({"error": "Missing 'dataset_info'"}), 400

    dataset = _create_dataset_from_dataset_info(dataset_info, current_user)

    # Observations
    created_obs = []
    for obs in observations:
        try:
            obs_date = datetime.fromisoformat(obs.get("observation_date")).date()
        except Exception:
            return jsonify({"error": f"Invalid observation_date for observation {obs}"}), 400

        new_obs = AstronomyObservation(
            data_set_id=dataset.id,
            object_name=obs.get("object_name"),
            ra=obs.get("ra"),
            dec=obs.get("dec"),
            magnitude=obs.get("magnitude"),
            observation_date=obs_date,
            filter_used=obs.get("filter_used"),
            notes=obs.get("notes"),
        )
        db.session.add(new_obs)
        created_obs.append(new_obs)

    # Attachments (metadatos; si quieres binarios, enlaza con Hubfile en otro paso)
    created_atts = []
    for att in attachments:
        new_att = AstronomyAttachment(
            data_set_id=dataset.id,
            file_name=att.get("file_name"),
            type=att.get("type"),
            description=att.get("description"),
            size_mb=att.get("size_mb"),
        )
        db.session.add(new_att)
        created_atts.append(new_att)

    db.session.commit()

    return jsonify({
        "message": "Astronomy dataset created",
        "dataset_id": dataset.id,
        "observations_count": len(created_obs),
        "attachments_count": len(created_atts),
        "detail_url": url_for("dataset.dataset_detail", dataset_id=dataset.id, _external=False),
    }), 201
