import re

import pytest

from app import db

# TESTS UNITARIOS PARA FakenodoService


class FakeMeta:
    def __init__(self, title):
        self.title = title


class FakeDataSet:
    def __init__(self, title):
        self.ds_meta_data = FakeMeta(title)


@pytest.fixture
def client():
    from app import create_app

    app = create_app("testing")

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
        yield client


def test_connection(client):
    response = client.get("/fakenodo/api")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "success"
    assert data["message"] == "Connected to FakenodoAPI"


def test_create_new_deposition_route(client):
    dataset_payload = {"title": "Test Dataset for Fakenodo"}
    response = client.post("/fakenodo/api/deposit/depositions", json={"metadata": {"title": dataset_payload["title"]}})
    assert response.status_code == 201
    data = response.get_json()

    assert data["id"] == 1
    assert data["metadata"]["title"] == dataset_payload["title"]
    assert data["files"] == []
    assert data["doi"] is None
    assert data["published"] is False


def test_get_all_depositions(client):
    response = client.get("/fakenodo/api/deposit/depositions")
    assert response.status_code == 200
    data = response.get_json()
    assert "depositions" in data
    assert isinstance(data["depositions"], list)
    assert len(data["depositions"]) == 1


def test_get_deposition(client):
    deposition_id = "1"
    response = client.get(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["id"] == int(deposition_id)
    assert data["metadata"]["title"] == "Test Dataset for Fakenodo"


def test_get_deposition_not_found(client):
    deposition_id = "999"
    response = client.get(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert data["message"] == "Deposition not found"


def test_upload_file(client):
    deposition_id = 1
    response = client.post(
        f"/fakenodo/api/deposit/depositions/{deposition_id}/files", data={"filename": "testfile.txt"}
    )
    assert response.status_code == 201
    data = response.get_json()
    assert data["filename"] == "testfile.txt"
    assert re.match(r"http://fakenodo.org/files/1/files/testfile.txt", data["link"])


def test_upload_file_deposition_not_found(client):
    deposition_id = 999
    response = client.post(
        f"/fakenodo/api/deposit/depositions/{deposition_id}/files", data={"filename": "testfile.txt"}
    )
    assert response.status_code == 404
    data = response.get_json()
    assert data["message"] == "Deposition not found"


def test_publish_deposition(client):
    deposition_id = 1
    response = client.post(f"/fakenodo/api/deposit/depositions/{deposition_id}/actions/publish")
    assert response.status_code == 202
    data = response.get_json()
    assert data["id"] == deposition_id
    assert data["doi"] == f"10.5072/fakenodo.{deposition_id}"


def test_publish_deposition_not_found(client):
    deposition_id = 999
    response = client.post(f"/fakenodo/api/deposit/depositions/{deposition_id}/actions/publish")
    assert response.status_code == 404
    data = response.get_json()
    assert data["message"] == "Deposition not found"


def test_delete_deposition(client):
    deposition_id = 1
    response = client.delete(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["message"] == "Deposition deleted"

    response = client.get(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 404


def test_delete_deposition_not_found(client):
    deposition_id = 999
    response = client.delete(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 404
    data = response.get_json()
    assert data["message"] == "Deposition not found"
