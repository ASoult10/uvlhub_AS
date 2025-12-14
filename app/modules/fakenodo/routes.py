import itertools
from typing import Dict

from flask import jsonify, render_template, request

from app.modules.fakenodo import fakenodo_bp

from app.modules.fakenodo.services import FakenodoService

# Creamos un único servicio compartido (singleton en el módulo)
fakenodo_service = FakenodoService()


# Ruta de prueba de conexión (GET /fakenodo/api)
@fakenodo_bp.route("", methods=["GET"])
def test_connection_fakenodo():
    response = {"status": "success", "message": "Connected to FakenodoAPI"}
    return jsonify(response)


# Ruta para eliminar un depósito (DELETE
# /fakenodo/api/deposit/depositions/<depositionId>)
@fakenodo_bp.route("/deposit/depositions/<depositionId>", methods=["DELETE"])
def delete_deposition_fakenodo(depositionId):
    deleted = fakenodo_service.delete_deposition(depositionId)
    if deleted:
        return jsonify({"message": "Deposition deleted"}), 200
    else:
        return jsonify({"message": "Deposition not found"}), 404


# Simulación de obtención de todos los depósitos (GET
# /fakenodo/api/deposit/depositions)
@fakenodo_bp.route("/deposit/depositions", methods=["GET"])
def get_all_depositions():
    return jsonify(fakenodo_service.get_all_depositions()), 200


# Simulación de creación de un nuevo depósito (POST
# /fakenodo/api/deposit/depositions)
@fakenodo_bp.route("/deposit/depositions", methods=["POST"])
def create_new_deposition():
    payload = request.get_json() or {}
    record = fakenodo_service.create_new_deposition(payload)
    return jsonify(record), 201


# Simulación de subida de archivo (POST
# /fakenodo/api/deposit/depositions/<deposition_id>/files)
@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>/files", methods=["POST"])
def upload_file(deposition_id):
    record = fakenodo_service.get_deposition(deposition_id)
    if not record:
        return jsonify({"message": "Deposition not found"}), 404

    filename = request.form.get("filename") or "unnamed_file"

    # Creamos un objeto minimalista compatible con la firma que espera el servicio
    class _Hubfile:
        def __init__(self, name):
            self.name = name

    hubfile = _Hubfile(filename)
    dummy_dataset = type("DummyDataset", (), {"user_id": None, "id": ""})()

    result = fakenodo_service.upload_file(dummy_dataset, deposition_id, hubfile)
    if result is None:
        return jsonify({"message": "Deposition not found"}), 404
    return jsonify(result), 201

# Simulación de publicación de depósito (POST
# /fakenodo/api/deposit/depositions/<deposition_id>/actions/publish)
@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>/actions/publish", methods=["POST"])
def publish_deposition(deposition_id):
    result = fakenodo_service.publish_deposition(deposition_id)
    if not result:
        return jsonify({"message": "Deposition not found"}), 404
    return jsonify(result), 202


# Simulación de obtención de detalles del depósito (GET
# /fakenodo/api/deposit/depositions/<deposition_id>)
@fakenodo_bp.route("/deposit/depositions/<int:deposition_id>", methods=["GET"])
def get_deposition(deposition_id):
    record = fakenodo_service.get_deposition(deposition_id)
    if not record:
        return jsonify({"message": "Deposition not found"}), 404
    else:
        return jsonify(record), 200


# Renderizar la vista de Fakenodo


@fakenodo_bp.route("/view", methods=["GET"])
def fakenodo_index():
    return render_template("fakenodo/index.html")
