import pytest
from app.modules.fakenodo.services import FakenodoService
import re
from app import db, create_app

# TESTS UNITARIOS PARA FakenodoService

class FakeMeta:
    def __init__(self, title):
        self.title = title

class FakeDataSet:
    def __init__(self, title):
        self.ds_meta_data = FakeMeta(title)

def test_create_new_deposition_successful():
    fakenodo_service = FakenodoService()
    dataset = FakeDataSet(title="My Test Dataset")

    response = fakenodo_service.create_new_deposition(dataset)

    assert response.get("status_code") == 201
    doi = response.get("fakenodo_doi")
    assert doi is not None

    pattern = rf"^\d{{2}}\.\d{{4}}/{re.escape(dataset.ds_meta_data.title)}$"
    assert re.match(pattern, doi)

def test_create_new_deposition_including_title():
    fakenodo_service = FakenodoService()
    dataset_title = "Galaxy"
    dataset = FakeDataSet(title=dataset_title)
    response = fakenodo_service.create_new_deposition(dataset)

    doi = response.get("fakenodo_doi")
    assert dataset_title in doi

def test_create_new_deposition_different_titles():
    fakenodo_service = FakenodoService()
    dataset1 = FakeDataSet(title="Dataset One")
    dataset2 = FakeDataSet(title="Dataset Two")

    response1 = fakenodo_service.create_new_deposition(dataset1)
    response2 = fakenodo_service.create_new_deposition(dataset2)

    doi1 = response1.get("fakenodo_doi")
    doi2 = response2.get("fakenodo_doi")

    assert doi1 != doi2

# TESTS PARA FakenodoRoutes

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
    response = client.get("/fakenodo/api/")
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == "success"
    assert data['message'] == "Connected to FakenodoAPI"
'''
def test_delete_deposition(client):
    deposition_id = "12345"
    response = client.delete(f"/fakenodo/api/deposit/depositions/{deposition_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == "success"
    assert data['message'] == f"Succesfully deleted deposition {deposition_id}"
'''