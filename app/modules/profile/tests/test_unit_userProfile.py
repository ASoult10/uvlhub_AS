import pytest

from app import db
from app.modules.auth.models import User
from app.modules.conftest import logout
from app.modules.dataset.models import DataSet, DSMetaData, PublicationType
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    Creates a user with profile and 2 datasets for testing author_profile route.
    """
    with test_client.application.app_context():
        # Create test user with profile
        user_test = User(email="author@example.com", password="test1234")
        db.session.add(user_test)
        db.session.commit()

        profile = UserProfile(
            user_id=user_test.id, name="John", surname="Doe", affiliation="Test University", orcid="0000-0001-2345-6789"
        )
        db.session.add(profile)
        db.session.commit()

        # Create datasets for the user
        # Dataset 1 with 5 downloads
        meta1 = DSMetaData(
            title="Dataset 1",
            description="First test dataset",
            publication_type=PublicationType.DATA_PAPER,
            tags="test, dataset1",
        )
        db.session.add(meta1)
        db.session.commit()

        dataset1 = DataSet(user_id=user_test.id, ds_meta_data_id=meta1.id, download_count=5)
        db.session.add(dataset1)

        # Dataset 2 with 10 downloads
        meta2 = DSMetaData(
            title="Dataset 2",
            description="Second test dataset",
            publication_type=PublicationType.OBSERVATION_DATA,
            tags="observation, test, dataset2",
        )
        db.session.add(meta2)
        db.session.commit()

        dataset2 = DataSet(user_id=user_test.id, ds_meta_data_id=meta2.id, download_count=10)
        db.session.add(dataset2)

        db.session.commit()

        # Store user_id for tests
        test_client.test_user_id = user_test.id

    yield test_client


def test_author_profile_public_access(test_client):
    """
    Tests public access to an author's profile page.
    Verifies that the page is accessible and displays correct author information.
    """
    logout(test_client)  # Ensure no user is logged in

    response = test_client.get(f"/profile/{test_client.test_user_id}")

    assert response.status_code == 200, "The author profile page could not be accessed."
    assert b"John" in response.data, "Author name is not present on the page."
    assert b"Doe" in response.data, "Author surname is not present on the page."


def test_author_profile_displays_datasets(test_client):
    """
    Tests that the author's profile page displays their datasets correctly.
    """
    response = test_client.get(f"/profile/{test_client.test_user_id}")
    assert response.status_code == 200
    assert b"Dataset 1" in response.data, "First dataset is not displayed."
    assert b"Dataset 2" in response.data, "Second dataset is not displayed."


def test_author_profile_datasets_counter(test_client):
    """
    Tests that the author's profile page displays the correct number of datasets.
    """
    response = test_client.get(f"/profile/{test_client.test_user_id}")
    assert response.status_code == 200
    # The datasets_counter should be 2 (two datasets created in fixture)
    assert b"2 datasets" in response.data, "Dataset counter is incorrect."


def test_author_profile_downloads_counter(test_client):
    """
    Tests that the author's profile page displays the correct total downloads count.
    The total should be 15 (5 + 10 from the two datasets).
    """
    response = test_client.get(f"/profile/{test_client.test_user_id}")
    assert response.status_code == 200
    # The downloads_counter should be 15 (5 + 10)
    assert b"15 downloads" in response.data, "Downloads counter is incorrect."


def test_author_profile_with_affiliation_and_orcid(test_client):
    """
    Tests that the author's profile page displays affiliation and ORCID information.
    """
    response = test_client.get(f"/profile/{test_client.test_user_id}")
    assert response.status_code == 200
    assert b"Test University" in response.data, "Author affiliation is not displayed."
    assert b"0000-0001-2345-6789" in response.data, "Author ORCID is not displayed."


def test_author_profile_not_found(test_client):
    """
    Tests that accessing a non-existent user's profile returns a 404 error.
    """
    response = test_client.get("/profile/99999")
    assert response.status_code == 404, "Expected 404 for non-existent user."
