import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import login, logout
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType
from app.modules.dataset.models_comments import CommentStatus, DSComment


@pytest.fixture(scope="module")
def test_client(test_client):
    with test_client.application.app_context():
        owner = User(email="owner@example.com", password="test1234")
        other = User(email="other@example.com", password="test1234")
        db.session.add_all([owner, other])
        db.session.commit()

        meta = DSMetaData(
            title="Test dataset title",
            description="Test dataset description",
            publication_type=PublicationType.DATA_PAPER,
        )
        db.session.add(meta)
        db.session.commit()

        dataset = DataSet(
            user_id=owner.id,
            ds_meta_data_id=meta.id,
        )
        db.session.add(dataset)
        db.session.commit()

    yield test_client


def _get_owner_and_dataset():
    owner = User.query.filter_by(email="owner@example.com").first()
    dataset = DataSet.query.filter_by(user_id=owner.id).first()
    return owner, dataset


def _get_other_user():
    return User.query.filter_by(email="other@example.com").first()


def test_list_dataset_comments_only_visible(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()

        visible_comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Visible comment for list",
            status=CommentStatus.VISIBLE,
        )
        hidden_comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Hidden comment for list",
            status=CommentStatus.HIDDEN,
        )
        pending_comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Pending comment for list",
            status=CommentStatus.PENDING,
        )

        db.session.add_all([visible_comment, hidden_comment, pending_comment])
        db.session.commit()

        dataset_id = dataset.id

    response = test_client.get(f"/dataset/{dataset_id}/comments/")
    assert response.status_code == 200

    json_data = response.get_json()
    contents = [c.get("content") for c in json_data]

    assert "Visible comment for list" in contents
    assert "Hidden comment for list" not in contents
    assert "Pending comment for list" not in contents


def test_create_dataset_comment_success(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()
        dataset_id = dataset.id
        owner_email = owner.email

    login_response = login(test_client, owner_email, "test1234")
    assert login_response.status_code in (200, 302)

    payload = {"content": "New test comment"}
    response = test_client.post(f"/dataset/{dataset_id}/comments/", json=payload)

    assert response.status_code == 201
    json_data = response.get_json()

    assert json_data.get("content") == "New test comment"

    with test_client.application.app_context():
        comment_id = json_data.get("id")
        comment = DSComment.query.filter_by(id=comment_id).first()
        assert comment is not None
        assert comment.dataset_id == dataset_id
        assert comment.status == CommentStatus.VISIBLE

    logout(test_client)


def test_create_dataset_comment_empty_content_returns_400(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()
        dataset_id = dataset.id
        owner_email = owner.email

    login_response = login(test_client, owner_email, "test1234")
    assert login_response.status_code in (200, 302)

    payload = {"content": "   "}
    response = test_client.post(f"/dataset/{dataset_id}/comments/", json=payload)

    assert response.status_code == 400
    json_data = response.get_json()
    assert "Content cannot be empty" in json_data.get("error", "")

    logout(test_client)


def test_create_dataset_comment_dataset_not_found_returns_400(test_client):
    with test_client.application.app_context():
        owner, _ = _get_owner_and_dataset()
        owner_email = owner.email

        from sqlalchemy import func

        max_id = db.session.query(func.max(DataSet.id)).scalar() or 0
        invalid_dataset_id = max_id + 1000

    login_response = login(test_client, owner_email, "test1234")
    assert login_response.status_code in (200, 302)

    payload = {"content": "Comment for non-existing dataset"}
    response = test_client.post(f"/dataset/{invalid_dataset_id}/comments/", json=payload)

    assert response.status_code == 400
    json_data = response.get_json()
    assert "Dataset not found" in json_data.get("error", "")

    logout(test_client)


def test_moderate_comment_hide_as_owner(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()

        comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Comment to hide",
            status=CommentStatus.VISIBLE,
        )
        db.session.add(comment)
        db.session.commit()

        dataset_id = dataset.id
        comment_id = comment.id
        owner_email = owner.email

    login_response = login(test_client, owner_email, "test1234")
    assert login_response.status_code in (200, 302)

    response = test_client.post(
        f"/dataset/{dataset_id}/comments/{comment_id}/moderate",
        json={"action": "hide"},
    )

    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data.get("success") is True

    with test_client.application.app_context():
        updated = DSComment.query.filter_by(id=comment_id).first()
        assert updated is not None
        assert updated.status == CommentStatus.HIDDEN

    logout(test_client)


def test_moderate_comment_forbidden_for_non_owner(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()
        other = _get_other_user()

        comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Comment non-owner tries to hide",
            status=CommentStatus.VISIBLE,
        )
        db.session.add(comment)
        db.session.commit()

        dataset_id = dataset.id
        comment_id = comment.id
        other_email = other.email

    login_response = login(test_client, other_email, "test1234")
    assert login_response.status_code in (200, 302)

    response = test_client.post(
        f"/dataset/{dataset_id}/comments/{comment_id}/moderate",
        json={"action": "hide"},
    )

    assert response.status_code == 403
    json_data = response.get_json()
    assert "permission" in json_data.get("error", "").lower()

    with test_client.application.app_context():
        unchanged = DSComment.query.filter_by(id=comment_id).first()
        assert unchanged is not None
        assert unchanged.status == CommentStatus.VISIBLE

    logout(test_client)


def test_moderate_comment_unknown_action_returns_400(test_client):
    with test_client.application.app_context():
        owner, dataset = _get_owner_and_dataset()

        comment = DSComment(
            dataset_id=dataset.id,
            author_id=owner.id,
            content="Comment for unknown action",
            status=CommentStatus.VISIBLE,
        )
        db.session.add(comment)
        db.session.commit()

        dataset_id = dataset.id
        comment_id = comment.id
        owner_email = owner.email

    login_response = login(test_client, owner_email, "test1234")
    assert login_response.status_code in (200, 302)

    response = test_client.post(
        f"/dataset/{dataset_id}/comments/{comment_id}/moderate",
        json={"action": "invalid_action"},
    )

    assert response.status_code == 400
    json_data = response.get_json()
    assert "Unknown action" in json_data.get("error", "")

    logout(test_client)
