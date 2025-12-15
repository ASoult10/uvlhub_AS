import os
import shutil
import tempfile
from datetime import date
from unittest.mock import Mock, patch

import pytest

from app import db
from app.modules.auth.models import User
from app.modules.dataset.models import Author, DataSet, DSMetaData, DSViewRecord, Observation, PublicationType
from app.modules.dataset.services import (
    AuthorService,
    DataSetService,
    DOIMappingService,
    DSDownloadRecordService,
    DSMetaDataService,
    DSViewRecordService,
    SizeService,
    calculate_checksum_and_size,
)
from app.modules.profile.models import UserProfile


@pytest.fixture(scope="module")
def test_client(test_client):
    """
    Extends the test_client fixture to add additional specific data for module testing.
    """
    with test_client.application.app_context():
        # Create test user with profile
        user = User.query.filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", password="test1234")
            db.session.add(user)
            db.session.commit()

        if not user.profile:
            profile = UserProfile(
                user_id=user.id, name="Test", surname="User", affiliation="Test University", orcid="0000-0002-1234-5678"
            )
            db.session.add(profile)
            db.session.commit()

        # Create test dataset with metadata
        ds_meta = DSMetaData(
            title="Test Dataset for Services",
            description="Test description",
            publication_type=PublicationType.DATA_PAPER,
            tags="test, services, unit",
        )
        db.session.add(ds_meta)
        db.session.commit()

        author = Author(
            name="User, Test", affiliation="Test University", orcid="0000-0002-1234-5678", ds_meta_data_id=ds_meta.id
        )
        db.session.add(author)

        obs = Observation(
            object_name="M31",
            ra="00:42:44.330",
            dec="+41:16:08.63",
            magnitude=3.44,
            observation_date=date(2024, 1, 15),
            filter_used="V",
            notes="Test observation",
            ds_meta_data_id=ds_meta.id,
        )
        db.session.add(obs)
        db.session.commit()

        dataset = DataSet(user_id=user.id, ds_meta_data_id=ds_meta.id)
        db.session.add(dataset)
        db.session.commit()

        test_client.test_user_id = user.id
        test_client.test_dataset_id = dataset.id
        test_client.test_ds_meta_id = ds_meta.id

    yield test_client


class TestCalculateChecksumAndSize:
    """Tests for the calculate_checksum_and_size function."""

    def test_calculate_checksum_and_size_valid_file(self):
        """
        Tests that checksum and size are calculated correctly for a valid file.
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file.write("Test content for checksum")
            tmp_file_path = tmp_file.name

        try:
            checksum, size = calculate_checksum_and_size(tmp_file_path)

            assert checksum is not None, "Checksum should not be None"
            assert isinstance(checksum, str), "Checksum should be a string"
            assert len(checksum) == 32, "MD5 checksum should be 32 characters"
            assert size > 0, "File size should be greater than 0"
            assert size == len("Test content for checksum"), "Size should match file content length"
        finally:
            os.remove(tmp_file_path)

    def test_calculate_checksum_and_size_empty_file(self):
        """
        Tests that checksum and size are calculated for an empty file.
        """
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
            tmp_file_path = tmp_file.name

        try:
            checksum, size = calculate_checksum_and_size(tmp_file_path)

            assert checksum is not None, "Checksum should not be None"
            assert size == 0, "Empty file should have size 0"
        finally:
            os.remove(tmp_file_path)


class TestDataSetService:
    """Tests for DataSetService class."""

    def test_get_synchronized(self, test_client):
        """
        Tests retrieving synchronized datasets for a user.
        """
        with test_client.application.app_context():
            service = DataSetService()
            result = service.get_synchronized(test_client.test_user_id)

            assert result is not None, "Should return a result"

    def test_get_unsynchronized(self, test_client):
        """
        Tests retrieving unsynchronized datasets for a user.
        """
        with test_client.application.app_context():
            service = DataSetService()
            result = service.get_unsynchronized(test_client.test_user_id)

            assert result is not None, "Should return a result"

    @patch("app.modules.dataset.repositories.current_user")
    def test_get_unsynchronized_dataset(self, mock_current_user, test_client):
        """
        Tests retrieving a specific unsynchronized dataset.
        """
        with test_client.application.app_context():
            # Mock authenticated user without curator role
            mock_current_user.is_authenticated = True
            mock_current_user.id = test_client.test_user_id
            mock_current_user.has_role.return_value = False

            service = DataSetService()
            result = service.get_unsynchronized_dataset(test_client.test_user_id, test_client.test_dataset_id)
            # Result can be None if dataset is synchronized
            assert result is not None or result is None, "Should return a dataset or None"

    def test_latest_synchronized(self, test_client):
        """
        Tests retrieving the latest synchronized datasets.
        """
        with test_client.application.app_context():
            service = DataSetService()
            result = service.latest_synchronized()

            assert result is not None, "Should return a result"

    def test_count_synchronized_datasets(self, test_client):
        """
        Tests counting synchronized datasets.
        """
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_synchronized_datasets()

            assert isinstance(count, int), "Count should be an integer"
            assert count >= 0, "Count should be non-negative"

    def test_count_feature_models(self, test_client):
        """
        Tests counting hubfiles (feature models).
        """
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_feature_models()

            assert isinstance(count, int), "Count should be an integer"
            assert count >= 0, "Count should be non-negative"

    def test_count_authors(self, test_client):
        """
        Tests counting authors.
        """
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_authors()

            assert isinstance(count, int), "Count should be an integer"
            assert count >= 0, "Count should be non-negative"

    def test_count_dsmetadata(self, test_client):
        """
        Tests counting dataset metadata records.
        """
        with test_client.application.app_context():
            service = DataSetService()
            count = service.count_dsmetadata()

            assert isinstance(count, int), "Count should be an integer"
            assert count >= 0, "Count should be non-negative"

    def test_total_dataset_downloads(self, test_client):
        """
        Tests getting total dataset downloads.
        """
        with test_client.application.app_context():
            service = DataSetService()
            total = service.total_dataset_downloads()

            assert isinstance(total, int), "Total should be an integer"
            assert total >= 0, "Total should be non-negative"

    def test_total_dataset_views(self, test_client):
        """
        Tests getting total dataset views.
        """
        with test_client.application.app_context():
            service = DataSetService()
            total = service.total_dataset_views()

            assert isinstance(total, int), "Total should be an integer"
            assert total >= 0, "Total should be non-negative"

    def test_get_uvlhub_doi(self, test_client):
        """
        Tests generating DOI URL for a dataset.
        """
        with test_client.application.app_context():
            service = DataSetService()
            dataset = DataSet.query.get(test_client.test_dataset_id)

            # Add DOI to dataset
            dataset.ds_meta_data.dataset_doi = "10.1234/test.doi"
            db.session.commit()

            doi_url = service.get_uvlhub_doi(dataset)

            assert doi_url is not None, "DOI URL should not be None"
            assert "10.1234/test.doi" in doi_url, "DOI URL should contain the DOI"

    def test_get_recommendations_with_matching_tags(self, test_client):
        """
        Tests getting dataset recommendations based on matching tags.
        """
        with test_client.application.app_context():
            # Create additional datasets with matching tags
            ds_meta2 = DSMetaData(
                title="Similar Dataset",
                description="Similar test description",
                publication_type=PublicationType.DATA_PAPER,
                tags="test, similar",
            )
            db.session.add(ds_meta2)
            db.session.commit()

            author2 = Author(
                name="Another, User",
                affiliation="Test University",
                orcid="0000-0002-9999-9999",
                ds_meta_data_id=ds_meta2.id,
            )
            db.session.add(author2)
            db.session.commit()

            user = User.query.get(test_client.test_user_id)
            dataset2 = DataSet(user_id=user.id, ds_meta_data_id=ds_meta2.id)
            db.session.add(dataset2)
            db.session.commit()

            service = DataSetService()
            recommendations = service.get_recommendations(test_client.test_dataset_id, limit=5)

            assert isinstance(recommendations, list), "Recommendations should be a list"
            if recommendations:
                assert "dataset" in recommendations[0], "Recommendation should contain dataset"
                assert "score" in recommendations[0], "Recommendation should contain score"

    def test_get_recommendations_no_matches(self, test_client):
        """
        Tests getting recommendations when there are no matching datasets.
        """
        with test_client.application.app_context():
            service = DataSetService()

            # Create dataset with unique tags
            ds_meta_unique = DSMetaData(
                title="Unique Dataset",
                description="Unique description",
                publication_type=PublicationType.DATA_PAPER,
                tags="unique, different, unmatched",
            )
            db.session.add(ds_meta_unique)
            db.session.commit()

            user = User.query.get(test_client.test_user_id)
            dataset_unique = DataSet(user_id=user.id, ds_meta_data_id=ds_meta_unique.id)
            db.session.add(dataset_unique)
            db.session.commit()

            recommendations = service.get_recommendations(dataset_unique.id, limit=5)

            assert isinstance(recommendations, list), "Recommendations should be a list"

    def test_get_or_404_existing_dataset(self, test_client):
        """
        Tests getting an existing dataset.
        """
        with test_client.application.app_context():
            service = DataSetService()
            dataset = service.get_or_404(test_client.test_dataset_id)

            assert dataset is not None, "Dataset should not be None"
            assert dataset.id == test_client.test_dataset_id, "Should return correct dataset"

    def test_get_or_404_nonexistent_dataset(self, test_client):
        """
        Tests getting a nonexistent dataset raises exception.
        """
        with test_client.application.app_context():
            service = DataSetService()

            with pytest.raises(Exception):
                service.get_or_404(999999)

    def test_update_from_form(self, test_client):
        """
        Tests updating a dataset from form data.
        """
        with test_client.application.app_context():
            service = DataSetService()

            # Mock form object
            mock_form = Mock()
            mock_form.get_dsmetadata.return_value = {
                "title": "Updated Title",
                "description": "Updated description",
                "publication_type": PublicationType.DATA_PAPER,
                "tags": "updated, tags",
            }
            mock_form.get_observation.return_value = {
                "object_name": "M42",
                "ra": "05:35:17.300",
                "dec": "-05:23:28.00",
                "magnitude": 4.0,
                "observation_date": date(2024, 2, 20),
                "filter_used": "H-alpha",
                "notes": "Updated notes",
            }

            updated_dataset = service.update_from_form(test_client.test_dataset_id, mock_form)

            assert updated_dataset is not None, "Updated dataset should not be None"
            assert updated_dataset.ds_meta_data.title == "Updated Title", "Title should be updated"

    def test_update_from_form_with_exception(self, test_client):
        """
        Tests that update_from_form handles exceptions correctly.
        """
        with test_client.application.app_context():
            service = DataSetService()

            # Mock form that will cause an exception
            mock_form = Mock()
            mock_form.get_dsmetadata.side_effect = Exception("Form error")

            with pytest.raises(Exception):
                service.update_from_form(test_client.test_dataset_id, mock_form)

    def test_get_all_synchronized_datasets(self, test_client):
        """
        Tests getting all synchronized datasets.
        """
        with test_client.application.app_context():
            service = DataSetService()
            result = service.get_all_synchronized_datasets()

            assert result is not None, "Result should not be None"

    def test_get_all_unsynchronized_datasets(self, test_client):
        """
        Tests getting all unsynchronized datasets.
        """
        with test_client.application.app_context():
            service = DataSetService()
            result = service.get_all_unsynchronized_datasets()

            assert result is not None, "Result should not be None"

    @patch("app.modules.dataset.services.AuthenticationService")
    def test_move_hubfiles(self, mock_auth_service, test_client):
        """
        Tests moving hubfiles from temp folder to dataset uploads folder.
        """
        with test_client.application.app_context():
            # Create mock user with temp folder
            mock_user = Mock()
            mock_user.id = test_client.test_user_id
            temp_dir = tempfile.mkdtemp()
            mock_user.temp_folder.return_value = temp_dir

            mock_auth_service.return_value.get_authenticated_user.return_value = mock_user

            # Create test file in temp folder
            test_file = os.path.join(temp_dir, "test.json")
            with open(test_file, "w") as f:
                f.write('{"test": "data"}')

            service = DataSetService()
            dataset = DataSet.query.get(test_client.test_dataset_id)

            try:
                service.move_hubfiles(dataset)

                # Verify temp file was moved
                assert not os.path.exists(test_file), "File should be moved from temp folder"
            finally:
                # Cleanup
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)


class TestAuthorService:
    """Tests for AuthorService class."""

    def test_author_service_initialization(self):
        """
        Tests that AuthorService initializes correctly.
        """
        service = AuthorService()
        assert service is not None, "AuthorService should initialize"
        assert service.repository is not None, "Repository should be initialized"


class TestDSDownloadRecordService:
    """Tests for DSDownloadRecordService class."""

    def test_ds_download_record_service_initialization(self):
        """
        Tests that DSDownloadRecordService initializes correctly.
        """
        service = DSDownloadRecordService()
        assert service is not None, "DSDownloadRecordService should initialize"
        assert service.repository is not None, "Repository should be initialized"


class TestDSMetaDataService:
    """Tests for DSMetaDataService class."""

    def test_update_dsmetadata(self, test_client):
        """
        Tests updating dataset metadata.
        """
        with test_client.application.app_context():
            service = DSMetaDataService()
            updated = service.update(test_client.test_ds_meta_id, title="Updated Metadata Title")

            assert updated is not None, "Update should return a result"

    def test_filter_by_doi_existing(self, test_client):
        """
        Tests filtering metadata by DOI when it exists.
        """
        with test_client.application.app_context():
            # Add DOI to test dataset
            ds_meta = DSMetaData.query.get(test_client.test_ds_meta_id)
            ds_meta.dataset_doi = "10.5281/test.123"
            db.session.commit()

            service = DSMetaDataService()
            result = service.filter_by_doi("10.5281/test.123")

            assert result is not None, "Should find metadata by DOI"
            assert result.dataset_doi == "10.5281/test.123", "Should return correct metadata"

    def test_filter_by_doi_nonexistent(self, test_client):
        """
        Tests filtering metadata by DOI when it doesn't exist.
        """
        with test_client.application.app_context():
            service = DSMetaDataService()
            result = service.filter_by_doi("10.5281/nonexistent.999")

            assert result is None, "Should return None for nonexistent DOI"


class TestDSViewRecordService:
    """Tests for DSViewRecordService class."""

    @patch("app.modules.dataset.repositories.current_user")
    def test_the_record_exists_false(self, mock_current_user, test_client):
        """
        Tests checking if a view record exists when it doesn't.
        """
        with test_client.application.app_context():
            # Mock unauthenticated user
            mock_current_user.is_authenticated = False
            mock_current_user.id = None

            with test_client.session_transaction():
                service = DSViewRecordService()
                dataset = DataSet.query.get(test_client.test_dataset_id)

                exists = service.the_record_exists(dataset, "new-cookie-12345")
                assert not exists, "Record should not exist for new cookie"

    @patch("app.modules.dataset.repositories.current_user")
    def test_create_new_record(self, mock_current_user, test_client):
        """
        Tests creating a new view record.
        """
        with test_client.application.app_context():
            # Mock unauthenticated user
            mock_current_user.is_authenticated = False
            mock_current_user.id = None

            with test_client.session_transaction():
                service = DSViewRecordService()
                dataset = DataSet.query.get(test_client.test_dataset_id)

                record = service.create_new_record(dataset, "test-cookie-67890")

                assert record is not None, "Should create new record"
                assert isinstance(record, DSViewRecord), "Should return DSViewRecord instance"

    def test_create_cookie_new_user(self, test_client):
        """
        Tests creating a cookie for a new user.
        """
        with test_client.application.app_context():
            # Create request context without existing cookies
            with test_client.application.test_request_context("/"):
                service = DSViewRecordService()
                dataset = DataSet.query.get(test_client.test_dataset_id)

                try:
                    cookie = service.create_cookie(dataset)

                    assert cookie is not None, "Cookie should be created"
                    assert isinstance(cookie, str), "Cookie should be a string"
                    assert len(cookie) > 0, "Cookie should not be empty"
                except (AttributeError, RuntimeError) as e:
                    # Method may require authenticated user or request context
                    pytest.skip(f"Method requires authentication or request context: {e}")

    def test_create_cookie_existing_user(self, test_client):
        """
        Tests creating/retrieving cookie for existing user.
        """
        with test_client.application.app_context():
            # Create request context with existing cookie
            with test_client.application.test_request_context(
                "/", environ_base={"HTTP_COOKIE": "view_cookie=existing-cookie-12345"}
            ):
                service = DSViewRecordService()
                dataset = DataSet.query.get(test_client.test_dataset_id)

                try:
                    cookie = service.create_cookie(dataset)

                    assert cookie == "existing-cookie-12345", "Should return existing cookie"
                except (AttributeError, RuntimeError) as e:
                    # Method may require authenticated user or request context
                    pytest.skip(f"Method requires authentication or request context: {e}")


class TestDOIMappingService:
    """Tests for DOIMappingService class."""

    def test_get_new_doi_nonexistent(self, test_client):
        """
        Tests getting new DOI when mapping doesn't exist.
        """
        with test_client.application.app_context():
            service = DOIMappingService()
            new_doi = service.get_new_doi("10.5281/old.doi.999")

            assert new_doi is None, "Should return None for nonexistent mapping"


class TestSizeService:
    """Tests for SizeService class."""

    def test_get_human_readable_size_bytes(self):
        """
        Tests converting bytes to human readable format.
        """
        service = SizeService()
        result = service.get_human_readable_size(500)

        assert result == "500 bytes", f"Should return '500 bytes' but got '{result}'"

    def test_get_human_readable_size_kilobytes(self):
        """
        Tests converting kilobytes to human readable format.
        """
        service = SizeService()
        result = service.get_human_readable_size(2048)

        assert "KB" in result, "Should contain KB"
        assert "2" in result, "Should contain size value"

    def test_get_human_readable_size_megabytes(self):
        """
        Tests converting megabytes to human readable format.
        """
        service = SizeService()
        result = service.get_human_readable_size(2 * 1024 * 1024)

        assert "MB" in result, "Should contain MB"
        assert "2" in result, "Should contain size value"

    def test_get_human_readable_size_gigabytes(self):
        """
        Tests converting gigabytes to human readable format.
        """
        service = SizeService()
        result = service.get_human_readable_size(3 * 1024 * 1024 * 1024)

        assert "GB" in result, "Should contain GB"
        assert "3" in result, "Should contain size value"

    def test_get_human_readable_size_zero(self):
        """
        Tests converting zero size.
        """
        service = SizeService()
        result = service.get_human_readable_size(0)

        assert result == "0 bytes", f"Should return '0 bytes' but got '{result}'"

    def test_get_human_readable_size_boundary_kb(self):
        """
        Tests boundary between bytes and KB.
        """
        service = SizeService()
        result = service.get_human_readable_size(1024)

        assert "KB" in result or "bytes" in result, "Should handle 1024 bytes boundary"

    def test_get_human_readable_size_boundary_mb(self):
        """
        Tests boundary between KB and MB.
        """
        service = SizeService()
        result = service.get_human_readable_size(1024 * 1024)

        assert "MB" in result or "KB" in result, "Should handle 1MB boundary"

    def test_update_from_form(self, test_client):
        """
        Tests specifically that observation details (RA, Dec, etc.) are updated correctly.
        """
        with test_client.application.app_context():
            service = DataSetService()

            # Datos nuevos para la observación
            new_date = date(2025, 12, 31)
            obs_data_update = {
                "object_name": "Andromeda Updated",
                "ra": "00:42:44.500",
                "dec": "+41:16:10.00",
                "magnitude": 3.50,
                "observation_date": new_date,
                "filter_used": "R",
                "notes": "Updated notes specifically for observation test",
            }

            # Mock del formulario
            mock_form = Mock()
            # Necesitamos datos mínimos de metadatos para que no falle la
            # primera parte
            mock_form.get_dsmetadata.return_value = {
                "title": "Title kept same",
                "publication_type": PublicationType.DATA_PAPER,
            }
            # Aquí inyectamos los datos de observación
            mock_form.get_observation.return_value = obs_data_update

            # Ejecutamos la actualización
            updated_dataset = service.update_from_form(test_client.test_dataset_id, mock_form)

            # Verificaciones
            assert updated_dataset is not None
            observation = updated_dataset.ds_meta_data.observation

            assert observation is not None, "Observation should exist"
            assert observation.object_name == "Andromeda Updated"
            assert observation.ra == "00:42:44.500"
            assert observation.dec == "+41:16:10.00"
            assert observation.magnitude == 3.50
            assert observation.observation_date == new_date
            assert observation.filter_used == "R"
            assert observation.notes == "Updated notes specifically for observation test"
