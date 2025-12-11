import glob
import logging
import os
from datetime import date

from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required

from app.modules.dataset.model_import_service import ModelImportService
from app.modules.dataset.models import Observation, PublicationType
from app.modules.dataset.services import AuthorService, DataSetService, DSMetaDataService, calculate_checksum_and_size

logger = logging.getLogger(__name__)

import_api = Blueprint("import_api", __name__)

ALLOWED_EXTENSIONS = {".uvl", ".fits", ".csv", ".json", ".txt"}


# =====================================================
#   IMPORTAR DATASET COMPLETO DESDE ZIP O GITHUB
# =====================================================
@import_api.route("/api/v1/datasets/import-model", methods=["POST"])
@login_required
def import_model():

    dataset_service = DataSetService()
    dsmetadata_service = DSMetaDataService()
    author_service = AuthorService()

    github_url = request.form.get("github_url")
    zip_file = request.files.get("zip_file")

    # -------------------------------------------------
    # 1. DECIDIR ORIGEN: ZIP o GITHUB
    # -------------------------------------------------
    if github_url:
        result = ModelImportService.import_from_github(github_url, current_user)
    elif zip_file:
        result = ModelImportService.import_from_zip(zip_file, current_user)
    else:
        return jsonify({"error": "Provide github_url OR zip_file"}), 400

    if "error" in result:
        return jsonify({"error": result["error"]}), 400

    imported_path = result["path"]
    logger.info(f"[IMPORT] Files imported into: {imported_path}")

    # -------------------------------------------------
    # 2. BUSCAR ARCHIVOS PERMITIDOS
    # -------------------------------------------------
    found_files = []
    for ext in ALLOWED_EXTENSIONS:
        found_files.extend(glob.glob(os.path.join(imported_path, f"**/*{ext}"), recursive=True))

    if not found_files:
        return jsonify({"error": "No valid files (.uvl, .fits, .csv, .json, .txt) found."}), 400

    # -------------------------------------------------
    # 3. CREAR DSMetaData
    # -------------------------------------------------
    dsmeta = dsmetadata_service.repository.create(
        title="Imported Dataset",
        description=f"Imported automatically from {result['source']}",
        publication_type=PublicationType.NONE.value,
        tags="imported",
    )

    # IMPORTANT: commit para generar dsmeta.id
    dataset_service.repository.session.commit()

    # -------------------------------------------------
    # 3B. CREAR OBSERVATION MÍNIMA
    # -------------------------------------------------
    observation = Observation(
        ds_meta_data_id=dsmeta.id,
        object_name="Imported Object",
        ra="00:00:00",
        dec="+00:00:00",
        observation_date=date.today(),
        magnitude=None,
        filter_used=None,
        notes="Auto-generated during import",
    )
    dataset_service.repository.session.add(observation)

    # -------------------------------------------------
    # 3C. AUTOR PRINCIPAL (EL USUARIO LOGGEADO)
    # -------------------------------------------------
    author_service.repository.create(
        ds_meta_data_id=dsmeta.id,
        name=f"{current_user.profile.surname}, {current_user.profile.name}",
        affiliation=current_user.profile.affiliation,
        orcid=current_user.profile.orcid,
    )

    # -------------------------------------------------
    # 4. CREAR DATASET
    # -------------------------------------------------
    dataset = dataset_service.repository.create(user_id=current_user.id, ds_meta_data_id=dsmeta.id)

    # -------------------------------------------------
    # 5. PROCESAR ARCHIVOS → CREAR HUBFILES
    # -------------------------------------------------
    working_dir = os.getenv("WORKING_DIR", "")
    dest_dir = os.path.join(
        working_dir,
        "uploads",
        f"user_{
            current_user.id}",
        f"dataset_{
            dataset.id}",
    )
    os.makedirs(dest_dir, exist_ok=True)

    for file_path in found_files:
        filename = os.path.basename(file_path)

        checksum, size = calculate_checksum_and_size(file_path)

        hubfile = dataset_service.hubfilerepository.create(
            commit=False,
            name=filename,
            checksum=checksum,
            size=size,
            dataset_id=dataset.id,
        )

        # mover archivo
        os.rename(file_path, os.path.join(dest_dir, filename))

        dataset.hubfiles.append(hubfile)

    # -------------------------------------------------
    # 6. GUARDAR TODO
    # -------------------------------------------------
    dataset_service.repository.session.commit()

    # -------------------------------------------------
    # 7. RESPUESTA
    # -------------------------------------------------
    return jsonify({"message": "Dataset imported successfully", "dataset": dataset.to_dict()}), 200
