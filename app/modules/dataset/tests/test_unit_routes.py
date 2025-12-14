import pytest
import logging
import os
import shutil
from flask_login import current_user

from app import db
from app.modules.auth.models import Role, User
from app.modules.profile.models import UserProfile
from app.modules.dataset.models import DataSet, DSMetaData, Author, Observation, PublicationType
from app.modules.conftest import login, logout
from datetime import date

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

        # Create curator user
        curator = User(email="curator_test@example.com", password="curator1234")
        db.session.add(curator)
        db.session.commit()
        # Get curator role and assign it to user
        curator_role = Role.query.filter_by(name="curator").first()
        if not curator_role:
            curator_role = Role(name="curator", description="Curator user with elevated access")
            db.session.add(curator_role)
            db.session.commit()
        curator.add_role(curator_role)
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

        # Create another user with profile for testing
        other_user = User(email="other_user@example.com", password="other1234")
        db.session.add(other_user)
        db.session.commit()

        other_profile = UserProfile(
            user_id=other_user.id,
            name="Other",
            surname="TestUser",
            affiliation="Other University",
            orcid="0000-0003-9876-5432"
        )
        db.session.add(other_profile)
        db.session.commit()

        # Store credentials for tests
        test_client.guest_email = "guest_test@example.com"
        test_client.guest_password = "guest1234"
        test_client.curator_email = "curator_test@example.com"
        test_client.curator_password = "curator1234"
        test_client.regular_user_email = "test@example.com"
        test_client.regular_user_password = "test1234"
        test_client.other_user_email = "other_user@example.com"
        test_client.other_user_password = "other1234"

        # Create test datasets
        # Dataset 1: Belongs to regular_user, synchronized (with DOI)
        ds_meta1 = DSMetaData(
            title="M31 Andromeda Galaxy",
            description="Photometric observations of the Andromeda Galaxy",
            publication_type=PublicationType.DATA_PAPER,
            tags="M31, Andromeda, galaxy",
            dataset_doi="10.5281/zenodo.123456",
            deposition_id=123456
        )
        db.session.add(ds_meta1)
        db.session.commit()

        author1 = Author(
            name="User, Test",
            affiliation="Test University",
            orcid="0000-0002-1234-5678",
            ds_meta_data_id=ds_meta1.id
        )
        db.session.add(author1)

        obs1 = Observation(
            object_name="M31",
            ra="00:42:44.330",
            dec="+41:16:08.63",
            magnitude=3.44,
            observation_date=date(2024, 1, 15),
            filter_used="V",
            notes="Clear night observation",
            ds_meta_data_id=ds_meta1.id
        )
        db.session.add(obs1)
        db.session.commit()

        dataset1 = DataSet(
            user_id=regular_user.id,
            ds_meta_data_id=ds_meta1.id
        )
        db.session.add(dataset1)
        db.session.commit()

        # Dataset 2: Belongs to regular_user, unsynchronized (no DOI)
        ds_meta2 = DSMetaData(
            title="NGC 1234 Star Cluster",
            description="Deep imaging of NGC 1234 star cluster",
            publication_type=PublicationType.OBSERVATION_DATA,
            tags="NGC1234, star cluster, photometry"
        )
        db.session.add(ds_meta2)
        db.session.commit()

        author2 = Author(
            name="User, Test",
            affiliation="Test University",
            orcid="0000-0002-1234-5678",
            ds_meta_data_id=ds_meta2.id
        )
        db.session.add(author2)

        obs2 = Observation(
            object_name="NGC 1234",
            ra="10:20:30.000",
            dec="+45:30:20.00",
            magnitude=12.5,
            observation_date=date(2024, 2, 10),
            filter_used="R",
            notes="Preliminary observation",
            ds_meta_data_id=ds_meta2.id
        )
        db.session.add(obs2)
        db.session.commit()

        dataset2 = DataSet(
            user_id=regular_user.id,
            ds_meta_data_id=ds_meta2.id
        )
        db.session.add(dataset2)
        db.session.commit()

        # Dataset 3: Belongs to other_user, synchronized
        ds_meta3 = DSMetaData(
            title="Orion Nebula M42",
            description="High resolution imaging of Orion Nebula",
            publication_type=PublicationType.DATA_PAPER,
            tags="M42, Orion, nebula",
            dataset_doi="10.5281/zenodo.789012",
            deposition_id=789012
        )
        db.session.add(ds_meta3)
        db.session.commit()

        author3 = Author(
            name="TestUser, Other",
            affiliation="Other University",
            orcid="0000-0003-9876-5432",
            ds_meta_data_id=ds_meta3.id
        )
        db.session.add(author3)

        obs3 = Observation(
            object_name="M42",
            ra="05:35:17.300",
            dec="-05:23:28.00",
            magnitude=4.0,
            observation_date=date(2024, 3, 5),
            filter_used="H-alpha",
            notes="Excellent seeing conditions",
            ds_meta_data_id=ds_meta3.id
        )
        db.session.add(obs3)
        db.session.commit()

        dataset3 = DataSet(
            user_id=other_user.id,
            ds_meta_data_id=ds_meta3.id
        )
        db.session.add(dataset3)
        db.session.commit()

        # Dataset 4: Belongs to other_user, unsynchronized
        ds_meta4 = DSMetaData(
            title="Pleiades M45",
            description="Wide field imaging of Pleiades cluster",
            publication_type=PublicationType.OBSERVATION_DATA,
            tags="M45, Pleiades, open cluster"
        )
        db.session.add(ds_meta4)
        db.session.commit()

        author4 = Author(
            name="TestUser, Other",
            affiliation="Other University",
            orcid="0000-0003-9876-5432",
            ds_meta_data_id=ds_meta4.id
        )
        db.session.add(author4)

        obs4 = Observation(
            object_name="M45",
            ra="03:47:24.000",
            dec="+24:07:00.00",
            magnitude=1.6,
            observation_date=date(2024, 3, 20),
            filter_used="B",
            notes="Wide field survey",
            ds_meta_data_id=ds_meta4.id
        )
        db.session.add(obs4)
        db.session.commit()

        dataset4 = DataSet(
            user_id=other_user.id,
            ds_meta_data_id=ds_meta4.id
        )
        db.session.add(dataset4)
        db.session.commit()

        test_client.ds_meta1_title = ds_meta1.title  # Regular user's dataset
        test_client.ds_meta2_title = ds_meta2.title  # Regular user's dataset
        test_client.ds_meta3_title = ds_meta3.title  # Other user's dataset
        test_client.ds_meta4_title = ds_meta4.title  # Other user's dataset

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


class TestListDatasetRoute:
    """ Tests for the list datasets route. """
    list_datasets_url = "/dataset/list"

    def test_list_datasets_as_guest(self, test_client):
        """
        Tests that guest users cannot access the list datasets route.
        """
        # Ensure clean state - logout any previous user
        logout(test_client)

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
        response = test_client.get(self.list_datasets_url, follow_redirects=False)
        assert response.status_code == 302, "Should redirect guest users"
        assert response.headers["Location"] == "/", "Should redirect to index page"
        logout(test_client)

    def test_list_datasets_as_curator(self, test_client):
        """
        Tests that curator users can access the list datasets route.
        """
        # Ensure clean state
        logout(test_client)

        # Login as curator user
        login_response = login(test_client, test_client.curator_email, test_client.curator_password)
        assert login_response.status_code == 200, "Login should be successful"
        # Verify current user has curator role
        with test_client.application.app_context():
            with test_client.session_transaction():
                assert current_user.is_authenticated, "User should be authenticated"
                assert current_user.has_role("curator"), (
                    f"Current user should have curator role but role is {current_user.roles.all()}"
                )

        response = test_client.get(self.list_datasets_url, follow_redirects=False)
        assert response.status_code == 200, "Curator users should access the list datasets page"
        assert f"{test_client.ds_meta1_title}".encode() in response.data, "Dataset 1 title should be present"
        assert f"{test_client.ds_meta2_title}".encode() in response.data, "Dataset 2 title should be present"
        assert f"{test_client.ds_meta3_title}".encode() in response.data, "Dataset 3 title should be present"
        assert f"{test_client.ds_meta4_title}".encode() in response.data, "Dataset 4 title should be present"
        logout(test_client)

    def test_list_datasets_as_regular_user(self, test_client):
        """
        Tests that regular authenticated users can access the list datasets route.
        """
        # Ensure clean state
        logout(test_client)

        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        # Verify current user is regular user
        with test_client.application.app_context():
            with test_client.session_transaction():
                assert current_user.is_authenticated, "User should be authenticated"
                assert not current_user.has_role("guest"), "User should not have guest role"
                assert not current_user.has_role("curator"), "User should not have curator role"

        response = test_client.get(self.list_datasets_url, follow_redirects=False)
        assert response.status_code == 200, "Regular users should access the list datasets page"

        showing_own_datasets = (
            f"{test_client.ds_meta1_title}".encode() in response.data
            and f"{test_client.ds_meta2_title}".encode() in response.data
            )
        assert showing_own_datasets, "Own datasets titles should be present"

        showing_other_datasets = (
            f"{test_client.ds_meta3_title}".encode() in response.data
            or f"{test_client.ds_meta4_title}".encode() in response.data
            )
        assert not showing_other_datasets, "Other users' datasets titles should not be present"

        logout(test_client)

    def test_list_datasets_as_unauthenticated_user(self, test_client):
        """
        Tests that unauthenticated users are redirected to login page when accessing list datasets route.
        """
        with test_client.application.app_context():
            with test_client.session_transaction():
                if current_user.is_authenticated:
                    logout(test_client)
                assert not current_user.is_authenticated, "User should not be authenticated"

        response = test_client.get(self.list_datasets_url, follow_redirects=False)
        assert response.status_code == 302, "Should redirect unauthenticated users"
        assert "/login" in response.headers["Location"], (
            f"Should redirect to login page but was {response.headers['Location']}"
        )


def cleanup_temp_folder(test_client, user_email):
    """
    Helper function to clean up temporary folder for a given user.

    Args:
        test_client: The Flask test client
        user_email: Email of the user whose temp folder should be cleaned
    """
    with test_client.application.app_context():
        user = User.query.filter_by(email=user_email).first()
        if user:
            temp_folder = user.temp_folder()
            if os.path.exists(temp_folder):
                shutil.rmtree(temp_folder)


class TestUploadFileRoute:
    """ Tests for the upload file route. """
    upload_file_url = "/dataset/file/upload"

    def test_upload_file_as_unauthenticated_user(self, test_client):
        """
        Tests that unauthenticated users cannot access the upload file route.
        """

        response = test_client.post(self.upload_file_url, follow_redirects=False)
        assert response.status_code == 302, "Should redirect unauthenticated users"
        assert "/login" in response.headers["Location"], (
            f"Should redirect to login page but was {response.headers['Location']}"
        )

    def test_upload_file_as_guest_user(self, test_client):
        """
        Tests that guest users cannot access the upload file route.
        """
        # Ensure clean state - logout any previous user
        logout(test_client)

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

        response = test_client.post(self.upload_file_url, follow_redirects=False)
        assert response.status_code == 302, "Should redirect guest users"
        assert response.headers["Location"] == "/", "Should redirect to index page"
        logout(test_client)

    def test_upload_file_successfully(self, test_client):
        """
        POSITIVE TEST: Successfully uploads a JSON file.
        """
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        # Clean up temp folder
        cleanup_temp_folder(test_client, test_client.regular_user_email)

        # Prepare file upload
        json_file_path = "app/modules/dataset/json_examples/M31_Andromeda.json"

        with open(json_file_path, 'rb') as f:
            data = {
                'file': (f, 'M31_Andromeda.json')
            }

            response = test_client.post(
                self.upload_file_url,
                data=data,
                content_type='multipart/form-data',
                follow_redirects=False
            )

        assert response.status_code == 200, f"Should successfully upload file, got {response.status_code}"
        json_data = response.get_json()
        assert "message" in json_data, "Response should contain a message"
        assert "uploaded successfully" in json_data["message"].lower(), "Should confirm successful upload"
        assert "filename" in json_data, "Response should contain filename"
        assert json_data["filename"] == "M31_Andromeda.json", "Filename should match uploaded file"

        logout(test_client)

    def test_upload_file_rejects_non_json(self, test_client):
        """
        Tests that non-JSON files are rejected.
        """
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"
        cleanup_temp_folder(test_client, test_client.regular_user_email)
        # Try to upload a non-JSON file
        from io import BytesIO
        data = {
            'file': (BytesIO(b'This is not JSON'), 'test.txt')
        }

        response = test_client.post(
            self.upload_file_url,
            data=data,
            content_type='multipart/form-data',
            follow_redirects=False
        )

        assert response.status_code == 400, "Should reject non-JSON files"
        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "valid file" in json_data["message"].lower(), "Error should mention invalid file"

        logout(test_client)

    def test_upload_file_handles_duplicate_names(self, test_client):
        """
        Tests that duplicate filenames are handled by adding a counter.
        """
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        json_file_path = "app/modules/dataset/json_examples/M31_Andromeda.json"

        cleanup_temp_folder(test_client, test_client.regular_user_email)

        # Upload file first time
        with open(json_file_path, 'rb') as f:
            data = {
                'file': (f, 'M31_Andromeda.json')
            }
            response1 = test_client.post(
                self.upload_file_url,
                data=data,
                content_type='multipart/form-data',
                follow_redirects=False
            )

        assert response1.status_code == 200, "First upload should succeed"
        json_data1 = response1.get_json()
        assert json_data1["filename"] == "M31_Andromeda.json", (
            f"First filename should be original but was {json_data1['filename']}"
        )

        # Upload same file again
        with open(json_file_path, 'rb') as f:
            data = {
                'file': (f, 'M31_Andromeda.json')
            }
            response2 = test_client.post(
                self.upload_file_url,
                data=data,
                content_type='multipart/form-data',
                follow_redirects=False
            )

        assert response2.status_code == 200, "Second upload should succeed"
        json_data2 = response2.get_json()
        assert json_data2["filename"] == "M31_Andromeda (1).json", "Second filename should have counter"

        # Clean up temp folder
        with test_client.application.app_context():
            user = User.query.filter_by(email=test_client.regular_user_email).first()
            temp_folder = user.temp_folder()
            if os.path.exists(temp_folder):
                shutil.rmtree(temp_folder)

        logout(test_client)


class TestDeleteFileRoute:
    """ Tests for the delete file route. """
    delete_file_url = "/dataset/file/delete"

    def test_delete_file_as_unauthenticated_user(self, test_client):
        """
        Tests that unauthenticated users cannot access the delete file route.
        """
        logout(test_client)
        
        response = test_client.post(
            self.delete_file_url,
            json={"file": "test.json"},
            follow_redirects=False
        )
        assert response.status_code == 302, "Should redirect unauthenticated users"
        assert "/login" in response.headers["Location"], (
            f"Should redirect to login page but was {response.headers['Location']}"
        )

    def test_delete_file_as_guest_user(self, test_client):
        """
        Tests that guest users cannot delete files.
        """
        logout(test_client)
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

        response = test_client.post(
            self.delete_file_url,
            json={"file": "test.json"},
            follow_redirects=False
        )
        assert response.status_code == 302, "Should redirect guest users"
        assert response.headers["Location"] == "/", "Should redirect to index page"
        logout(test_client)

    def test_delete_file_successfully(self, test_client):
        """
        POSITIVE TEST: Successfully deletes an existing file.
        """
        logout(test_client)
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        # First, upload a file
        cleanup_temp_folder(test_client, test_client.regular_user_email)

        json_file_path = "app/modules/dataset/json_examples/M31_Andromeda.json"
        with open(json_file_path, 'rb') as f:
            data = {
                'file': (f, 'test_delete.json')
            }
            upload_response = test_client.post(
                "/dataset/file/upload",
                data=data,
                content_type='multipart/form-data',
                follow_redirects=False
            )

        assert upload_response.status_code == 200, "Upload should succeed"

        # Now delete the file
        response = test_client.post(
            self.delete_file_url,
            json={"file": "test_delete.json"},
            content_type='application/json',
            follow_redirects=False
        )

        assert response.status_code == 200, f"Should successfully delete file, got {response.status_code}"
        json_data = response.get_json()
        assert "message" in json_data, "Response should contain a message"
        assert "file deleted" in json_data["message"].lower(), "Should confirm successful deletion"
        assert json_data["filename"] == "test_delete.json", "Filename should match deleted file"

        # Clean up
        cleanup_temp_folder(test_client, test_client.regular_user_email)
        logout(test_client)

    def test_delete_file_not_found(self, test_client):
        """
        Tests that deleting a non-existent file returns 404.
        """
        logout(test_client)
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        # Clean up to ensure no files exist
        cleanup_temp_folder(test_client, test_client.regular_user_email)

        # Try to delete non-existent file
        response = test_client.post(
            self.delete_file_url,
            json={"file": "nonexistent.json"},
            content_type='application/json',
            follow_redirects=False
        )

        assert response.status_code == 404, "Should return 404 for non-existent file"
        json_data = response.get_json()
        assert "message" in json_data, "Response should contain error message"
        assert "file not found" in json_data["message"].lower(), "Error should mention file not found"

        logout(test_client)

    def test_delete_file_without_filename(self, test_client):
        """
        Tests that deleting without providing filename returns error.
        """
        # Login as regular user
        login_response = login(test_client, test_client.regular_user_email, test_client.regular_user_password)
        assert login_response.status_code == 200, "Login should be successful"

        # Try to delete without filename
        response = test_client.post(
            self.delete_file_url,
            json={},
            content_type='application/json',
            follow_redirects=False
        )

        # The route will try to delete a file with None name, which should fail
        assert response.status_code in [404, 500], "Should return error for missing filename"

        logout(test_client)
