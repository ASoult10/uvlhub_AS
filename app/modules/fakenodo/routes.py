from flask import jsonify, render_template, request

from app.modules.fakenodo import fakenodo_bp

_STATE: Dict[str, object] = {
    "next_id": itertools.count(1),
    "records": {},
}


# Ruta de prueba de conexión (GET /fakenodo/api)
@fakenodo_bp.route("", methods=["GET"])
def test_connection_fakenodo():
    response = {"status": "success", "message": "Connected to FakenodoAPI"}
    return jsonify(response)


# Ruta para eliminar un depósito (DELETE
# /fakenodo/api/deposit/depositions/<depositionId>)
@fakenodo_bp.route("/deposit/depositions/<depositionId>", methods=["DELETE"])
def delete_deposition_fakenodo(depositionId):
    deposition_id_int = int(depositionId)
    if deposition_id_int in _STATE["records"]:
        del _STATE["records"][deposition_id_int]
        return jsonify({"message": "Deposition deleted"}), 200
    else:
        return jsonify({"message": "Deposition not found"}), 404


# Simulación de obtención de todos los depósitos (GET
# /fakenodo/api/deposit/depositions)
@fakenodo_bp.route("/deposit/depositions", methods=["GET"])
def get_all_depositions():
    return jsonify({"depositions": list(_STATE["records"].values())}), 200


# Simulación de creación de un nuevo depósito (POST
# /fakenodo/api/deposit/depositions)
@fakenodo_bp.route("/deposit/depositions", methods=["POST"])
def create_new_deposition():

    payload = request.get_json() or {}
    metadata = payload.get("metadata", {})

    record_id = next(_STATE["next_id"])

    record = {"id": record_id, "metadata": metadata, "files": [], "doi": None, "published": False}
    _STATE["records"][record_id] = record
    return jsonify(record), 201


# Simulación de subida de archivo (POST
# /fakenodo/api/deposit/depositions/<deposition_id>/files)
@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>/files", methods=["POST"])
def upload_file(deposition_id):

    record = _STATE["records"].get(deposition_id)
    if not record:
        return jsonify({"message": "Deposition not found"}), 404

    filename = request.form.get("filename") or "unnamed_file"

    record["files"].append(
        {
            "filename": filename,
        }
    )

    return jsonify({"filename": filename, "link": f"http://fakenodo.org/files/{deposition_id}/files/{filename}"}), 201



# Simulación de publicación de depósito (POST
# /fakenodo/api/deposit/depositions/<deposition_id>/actions/publish)


@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>/actions/publish", methods=["POST"])
def publish_deposition(deposition_id):
    record = _STATE["records"].get(deposition_id)
    if not record:
        return jsonify({"message": "Deposition not found"}), 404

    doi = f"10.5072/fakenodo.{deposition_id}"
    record["doi"] = doi
    record["published"] = True

    return jsonify({"id": deposition_id, "doi": doi}), 202


# Simulación de obtención de detalles del depósito (GET
# /fakenodo/api/deposit/depositions/<deposition_id>)
@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>", methods=["GET"])
def get_deposition(deposition_id):
    record = _STATE["records"].get(deposition_id)
    if not record:
        return jsonify({"message": "Deposition not found"}), 404
    else:
        return jsonify(record), 200


# Renderizar la vista de Fakenodo


@fakenodo_bp.route("/view", methods=["GET"])
def fakenodo_index():
    return render_template("fakenodo/index.html")
