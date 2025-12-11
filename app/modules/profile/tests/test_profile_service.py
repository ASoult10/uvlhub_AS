# tests/test_profile_service.py
from flask import Flask
import pytest
from app import db
from app.modules.profile.forms import UserProfileForm
from app.modules.profile.models import UserProfile
from app.modules.profile.services import UserProfileService
from werkzeug.datastructures import MultiDict



@pytest.fixture
def service():
    return UserProfileService()


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    from app import db  # your SQLAlchemy instance
    db.init_app(app)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def app_context(app):
    with app.app_context():
        yield app


def test_update_profile_valid(service, app_context):
    user = UserProfile(id=1, user_id= 1, name="Old", surname="User", orcid="", affiliation="Old Uni")
    db.session.add(user)
    db.session.commit()

    form = UserProfileForm(
        data={
            "name": "John",
            "surname": "Doe",
            "orcid": "",
            "affiliation": "Uni"
        }
    )

    updated, error = service.update_profile(1, form)

    assert error is None
    assert updated is not None
    assert updated.name == "John"
    assert updated.surname == "Doe"


def test_update_profile_invalid(service, app_context):

    form = UserProfileForm(
        data={
            "name": "",
            "surname": "",
            "orcid": "",
            "affiliation": "Uni"
        }
    )

    updated, error = service.update_profile(1, form)

    assert updated is None
    assert error is not None
    assert "name" in error
    assert "surname" in error


def test_update_profile_with_invalid_orcid(service, app_context):
    user = UserProfile(id=1, user_id= 1, name="Old", surname="User", orcid="", affiliation="Old Uni")
    db.session.add(user)
    db.session.commit()


    form = UserProfileForm(
    formdata=MultiDict({
        "name": "John",
        "surname": "Doe",
        "orcid": "1234-5678-999",  # invalid
        "affiliation": "Uni"
    })
    )


    updated, error = service.update_profile(1, form)
    assert updated is None
    assert error is not None
    assert "orcid" in error

