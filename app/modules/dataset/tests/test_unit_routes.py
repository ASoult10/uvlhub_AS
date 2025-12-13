import pytest
import logging
from flask_login import current_user

from app import db
from app.modules.auth.models import Role, User
from app.modules.profile.models import UserProfile
from app.modules.conftest import login, logout

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Create guest user
        guest = User(email="guest_test@example.com", password="guest1234")
        db.session.add(guest)
        db.session.commit()

        # Get guest role and assign it to user
        guest_role = Role.query.filter_by(name="guest").first()
        if not guest_role:
            guest_role = Role(name="guest", description="Guest user with limited access")
            db.session.add(guest_role)
            db.session.commit()
        guest.add_role(guest_role)
        db.session.commit()

        # Create profile for regular test user
        regular_user = User.query.filter_by(email="test@example.com").first()
        if regular_user and not regular_user.profile:
            profile = UserProfile(
                user_id=regular_user.id,
                name="Test",
                surname="User",
                affiliation="Test University",
                orcid="0000-0002-1234-5678"
            )
            db.session.add(profile)
            db.session.commit()

        # Store credentials for tests
        test_client.guest_email = "guest_test@example.com"
        test_client.guest_password = "guest1234"
        test_client.regular_user_email = "test@example.com"
        test_client.regular_user_password = "test1234"

    yield test_client


@pytest.fixture(scope="module")
def valid_form_data():
    """
    Returns valid form data for testing including all required fields.
    """

    form_data = {
            'csrf_token': '',
            'title': 'M31 Andromeda Galaxy Dataset',
            'desc': 'Comprehensive observational data of the Andromeda Galaxy.',
            'publication_type': 'DATA_PAPER',
            'tags': 'M31, Andromeda, galaxy, photometry',
            # Author data
            'authors-0-name': 'Dr. Jane Smith',
            'authors-0-affiliation': 'Harvard-Smithsonian Center for Astrophysics',
            'authors-0-orcid': '0000-0001-2345-6789',
            # Observation data
            'observation-object_name': 'M31',
            'observation-ra': '00:42:44.330',
            'observation-dec': '+41:16:08.63',
            'observation-observation_date': '2024-01-15',  # DateField expects YYYY-MM-DD format
            'observation-magnitude': '3.44',
            'observation-filter_used': 'V',
            'observation-notes': 'Clear night, excellent seeing conditions'
        }
    return form_data


class TestCreateDatasetRoute:
    """ Tests for the create dataset route. """

    def test_guests_cannot_create_datasets(self, test_client):
        """
        Tests that authenticated guest users cannot create datasets.
        """
        # Login as guest user
        login_response = login(test_client, test_client.guest_email, test_client.guest_password)
        assert login_response.status_code == 200, "Login should be successful"

        # Verify current user has guest role
        with test_client.application.app_context():
            with test_client.session_transaction():
                assert current_user.is_authenticated, "User should be authenticated"
                assert current_user.has_role("guest"), (
                    f"Current user should have guest role but role is {current_user.roles.all()}"
                )

        # Attempt to access dataset creation
        response = test_client.get("/dataset/upload", follow_redirects=False)
        assert response.status_code == 302, "Should redirect guest users"
        assert response.headers["Location"] == "/", "Should redirect to index page"
        logout(test_client)

    def test_unauthenticated_users_cannot_access_create_dataset(self, test_client):
        """
        Tests that unauthenticated users are redirected to login page.
        """
        with test_client.application.app_context():
            with test_client.session_transaction():
                if current_user.is_authenticated:
                    logout(test_client)
                assert not current_user.is_authenticated, "User should not be authenticated"

        response = test_client.get("/dataset/upload", follow_redirects=False)
        assert response.status_code == 302, "Should redirect unauthenticated users"
        assert "/login" in response.headers["Location"], (
            f"Should redirect to login page but was {response.headers['Location']}"
        )

    def test_authenticated_regular_users_can_access_create_dataset_form(self, test_client):
        """
        Tests that authenticated regular users (non-guest) can access the dataset creation form.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        response = test_client.get("/dataset/upload", follow_redirects=False)
        assert response.status_code == 200, "Regular users should access the form"
        assert b"upload" in response.data or b"dataset" in response.data, "Should display the upload form"

    def test_create_dataset_post_requires_observation_data(self, test_client, valid_form_data):
        """
        Tests that POST request without observation data returns 400 error.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')
        valid_form_data_no_observation = valid_form_data.copy()
        # Remove observation fields
        keys_to_remove = [key for key in valid_form_data_no_observation if key.startswith('observation-')]
        for key in keys_to_remove:
            del valid_form_data_no_observation[key]

        response = test_client.post("/dataset/upload", json=valid_form_data_no_observation, follow_redirects=False)
        assert response.status_code == 400, "Should return 400 for missing observation data"

        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"

    def test_create_dataset_post_requires_object_name(self, test_client, valid_form_data):
        """
        Tests that POST request without object_name returns 400 error.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)

        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')

        valid_form_data_no_object_name = valid_form_data.copy()
        valid_form_data_no_object_name['observation-object_name'] = ""

        response = test_client.post(
            "/dataset/upload",
            data=valid_form_data_no_object_name,
            follow_redirects=False,
            content_type='application/x-www-form-urlencoded'
        )

        assert response.status_code == 400, "Should return 400 for missing object_name"
        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "object name" in str(json_data["message"]).lower(), "Error should mention object name"

    def test_create_dataset_post_requires_ra(self, test_client, valid_form_data):
        """
        Tests that POST request without RA returns 400 error.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)

        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')

        valid_form_data_no_ra = valid_form_data.copy()
        valid_form_data_no_ra['observation-ra'] = ""

        response = test_client.post(
            "/dataset/upload",
            data=valid_form_data_no_ra,
            follow_redirects=False,
            content_type='application/x-www-form-urlencoded'
        )
        assert response.status_code == 400, "Should return 400 for missing RA"

        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "ra" in str(json_data["message"]).lower(), "Error should mention ra"

    def test_create_dataset_post_requires_dec(self, test_client, valid_form_data):
        """
        Tests that POST request without DEC returns 400 error.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)

        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')

        valid_form_data_no_dec = valid_form_data.copy()
        valid_form_data_no_dec['observation-dec'] = ""

        response = test_client.post(
            "/dataset/upload",
            data=valid_form_data_no_dec,
            follow_redirects=False,
            content_type='application/x-www-form-urlencoded'
        )
        assert response.status_code == 400, "Should return 400 for missing DEC"

        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "dec" in str(json_data["message"]).lower(), "Error should mention dec"

    def test_create_dataset_post_requires_observation_date(self, test_client, valid_form_data):
        """
        Tests that POST request without observation_date returns 400 error.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)

        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')

        valid_form_data_no_observation_date = valid_form_data.copy()
        valid_form_data_no_observation_date['observation-observation_date'] = ""

        response = test_client.post(
            "/dataset/upload",
            data=valid_form_data_no_observation_date,
            follow_redirects=False,
            content_type='application/x-www-form-urlencoded'
        )
        assert response.status_code == 400, "Should return 400 for missing observation_date"

        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "observation date" in str(json_data["message"]).lower(), "Error should mention observation date"

    def test_create_dataset_successfully_with_form_data(self, test_client, valid_form_data):
        """
        POSITIVE TEST: Successfully creates a dataset with valid form data.
        This test sends data as form-encoded (how the actual HTML form works),
        not as JSON.
        """
        login(test_client, test_client.regular_user_email, test_client.regular_user_password)

        response = test_client.get("/dataset/upload")
        assert response.status_code == 200, "Should access the dataset upload form"

        with test_client.session_transaction() as sess:
            valid_form_data['csrf_token'] = sess.get('csrf_token', '')

        response = test_client.post("/dataset/upload", json=valid_form_data, follow_redirects=False)

        json_data = response.get_json()

        assert response.status_code == 200, "Should successfully create dataset"
        assert "message" in json_data, "Response should contain a message"
        assert "works" in json_data["message"].lower() or "success" in json_data["message"].lower()
