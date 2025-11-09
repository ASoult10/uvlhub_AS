from flask import jsonify
from app.modules.fakenodo import fakenodo_bp
from app.modules.fakenodo.services import FakenodoService
from flask import request


fakenodo_service = FakenodoService()

# Ruta de prueba de conexión (GET /fakenodo/api)
@fakenodo_bp.route('', methods=["GET"])
def test_connection_fakenodo():
    response = {"status": "success", "message": "Connected to FakenodoAPI"}
    return jsonify(response)


# Ruta para eliminar un depósito (DELETE /fakenodo/api/deposit/depositions/<depositionId>)
@fakenodo_bp.route('/deposit/depositions/<depositionId>', methods=["DELETE"])
def delete_deposition_fakenodo(depositionId):
    response = {
        "status": "success",
        "message": f"Succesfully deleted deposition {depositionId}",
    }
    return jsonify(response), 200


# Simulación de obtención de todos los depósitos (GET /fakenodo/api/deposit/depositions)
@fakenodo_bp.route('/deposit/depositions', methods=['GET'])
def get_all_depositions():
    # Simulamos una respuesta con una lista de depósitos
    fake_depositions = [
        {
            "id": 12345,
            "title": "Fake Deposition 1",
            "description": "This is a fake deposition created for testing.",
            "creators": [{"name": "John Doe"}],
            "published": True
        },
        {
            "id": 67890,
            "title": "Fake Deposition 2",
            "description": "Another fake deposition for testing.",
            "creators": [{"name": "Jane Smith"}],
            "published": False
        },
    ]
    return jsonify({"depositions": fake_depositions}), 200

# Simulación de creación de un nuevo depósito (POST /fakenodo/api/deposit/depositions)
@fakenodo_bp.route('/deposit/depositions', methods=['POST'])
def create_new_deposition():
    
    dataset_data = request.get_json() or {}
    fakenodo_dataset = type("FakeDataset", 
                            (), 
                            {"ds_meta_data": type("meta", (), {"title": dataset_data.get("title", "Untitled")})()}
                            )
    
    response = fakenodo_service.create_new_deposition(fakenodo_dataset)
    return jsonify(response), response.get("status_code", 201)


# Simulación de subida de archivo (POST /fakenodo/api/deposit/depositions/<deposition_id>/files)
@fakenodo_bp.route('/deposit/depositions/<int:deposition_id>/files', methods=['POST'])
def upload_file(deposition_id):
    return jsonify({
        "message": "File uploaded successfully"
    }), 201


# Simulación de publicación de depósito (POST /fakenodo/api/deposit/depositions/<deposition_id>/actions/publish)
@fakenodo_bp.route('/deposit/depositions/<int:deposition_id>/actions/publish', methods=['POST'])
def publish_deposition(deposition_id):
    # Simulamos la publicación del depósito con una respuesta 202 (Accepted)
    return jsonify({
        "id": deposition_id,
        "doi": f"10.5072/fakenodo.{deposition_id}"
    }), 202


# Simulación de obtención de detalles del depósito (GET /fakenodo/api/deposit/depositions/<deposition_id>)
@fakenodo_bp.route('/deposit/depositions/<int:deposition_id>', methods=['GET'])
def get_deposition(deposition_id):
    # Simulamos la obtención de los detalles del depósito con una respuesta 200 (OK)
    return jsonify({
        "id": deposition_id,
        "metadata": {
            "title": "Sample Deposition",
            "upload_type": "publication",
            "publication_type": "article",
            "description": "This is a sample description",
        },
        "files": [
            {"filename": "file1.txt", "filesize": 1024},
            {"filename": "file2.pdf", "filesize": 2048}
        ],
        "published": True
    }), 200


# Simulación de error 404 si el depósito no existe (GET /fakenodo/api/deposit/depositions/<deposition_id>/nonexistent)
@fakenodo_bp.route('/deposit/depositions/<int:deposition_id>/nonexistent', methods=['GET'])
def deposition_not_found(deposition_id):
    # Simulamos un error 404 (Not Found)
    return jsonify({"message": "Deposition not found"}), 404