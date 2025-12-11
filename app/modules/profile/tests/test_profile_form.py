from werkzeug.datastructures import MultiDict
import pytest
from flask import Flask
from app.modules.profile.forms import UserProfileForm

@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    app.config["WTF_CSRF_ENABLED"] = False  
    return app

def test_orcid_is_optional(app):
    with app.app_context():
        form = UserProfileForm(
            data={
                "name": "John",
                "surname": "Doe",
                "orcid": "",
                "affiliation": "Uni"
            }
        )
        assert form.validate() is True


def test_orcid_invalid_format(app):
    with app.app_context():
        form = UserProfileForm(
            formdata=MultiDict({
                "name": "John",
                "surname": "Doe",
                "orcid": "1234-5678-999",  # too short
                "affiliation": "Uni"
            })
        )
        assert not form.validate()
        assert "Invalid ORCID format" in form.orcid.errors[0]


def test_orcid_valid(app):
    with app.app_context():
        form = UserProfileForm(
            data={
                "name": "Alice",
                "surname": "Smith",
                "orcid": "0000-1111-2222-3333",
                "affiliation": "Uni"
            }
        )
        assert form.validate() is True

def test_required_fields_missing(app):
    with app.app_context():
        form = UserProfileForm(
            data={
                "name": "",
                "surname": "",
                "orcid": "",
                "affiliation": "Uni"
            }
        )
        assert form.validate() is False
        assert "This field is required." in form.name.errors
        assert "This field is required." in form.surname.errors
