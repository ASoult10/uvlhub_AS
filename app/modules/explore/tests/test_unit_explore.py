import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from app import create_app
from app.modules.dataset.models import PublicationType
from app.modules.explore.services import ExploreService


class TestExploreUnit:
    """
    Unit tests for the explore/dataset filtering system.
    Tests the logic without database or UI dependencies.
    """

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = create_app()
        app.config["TESTING"] = True
        return app

    @pytest.fixture
    def app_context(self, app):
        """Create application context"""
        with app.app_context():
            yield app

    @pytest.fixture
    def explore_service(self, app_context):
        """Create an ExploreService for testing"""
        return ExploreService()

    @pytest.fixture
    def sample_datasets(self):
        """Create sample datasets for testing filters"""
        datasets = []

        # Dataset 1: Alpha
        ds1 = Mock()
        ds1.id = 1
        ds1.created_at = datetime(2024, 1, 10)
        meta1 = Mock()
        meta1.title = "Alpha dataset"
        meta1.description = "Some interesting description"
        meta1.tags = "bio,geo"
        meta1.publication_type = PublicationType.JOURNAL_ARTICLE
        author1 = Mock()
        author1.name = "John Doe"
        author1.affiliation = "Uni Madrid"
        author1.orcid = "0000-0000-0000-0001"
        meta1.authors = [author1]
        ds1.ds_meta_data = meta1
        datasets.append(ds1)

        # Dataset 2: Beta
        ds2 = Mock()
        ds2.id = 2
        ds2.created_at = datetime(2024, 1, 15)
        meta2 = Mock()
        meta2.title = "Beta dataset"
        meta2.description = "Another description"
        meta2.tags = "chemistry,geo"
        meta2.publication_type = PublicationType.JOURNAL_ARTICLE
        author2 = Mock()
        author2.name = "John Doe"
        author2.affiliation = "Uni Madrid"
        author2.orcid = "0000-0000-0000-0001"
        meta2.authors = [author2]
        ds2.ds_meta_data = meta2
        datasets.append(ds2)

        # Dataset 3: Gamma
        ds3 = Mock()
        ds3.id = 3
        ds3.created_at = datetime(2024, 2, 27)
        meta3 = Mock()
        meta3.title = "Gamma dataset"
        meta3.description = "Meridian rocks"
        meta3.tags = "geo"
        meta3.publication_type = PublicationType.JOURNAL_ARTICLE
        author3 = Mock()
        author3.name = "Jules"
        author3.affiliation = "Uni Los Angeles"
        author3.orcid = "0000-0000-0000-0005"
        meta3.authors = [author3]
        ds3.ds_meta_data = meta3
        datasets.append(ds3)

        # Dataset 4: Epsilon
        ds4 = Mock()
        ds4.id = 4
        ds4.created_at = datetime(2024, 6, 5)
        meta4 = Mock()
        meta4.title = "Epsilon dataset"
        meta4.description = "Nombre del cuarto de libra con queso en Paris"
        meta4.tags = "medicine,geo"
        meta4.publication_type = PublicationType.JOURNAL_ARTICLE
        author4 = Mock()
        author4.name = "Hans Landa"
        author4.affiliation = "Uni Vienna"
        author4.orcid = "0000-0000-0000-0003"
        meta4.authors = [author4]
        ds4.ds_meta_data = meta4
        datasets.append(ds4)

        # Dataset 5: Delta
        ds5 = Mock()
        ds5.id = 5
        ds5.created_at = datetime(2024, 10, 10)
        meta5 = Mock()
        meta5.title = "Delta dataset"
        meta5.description = "Unrelated description"
        meta5.tags = "history,art"
        meta5.publication_type = PublicationType.JOURNAL_ARTICLE
        author5 = Mock()
        author5.name = "Mr Pink"
        author5.affiliation = "Uni Los Angeles"
        author5.orcid = "0000-0000-0000-0004"
        meta5.authors = [author5]
        ds5.ds_meta_data = meta5
        datasets.append(ds5)

        # Dataset 6: Sigma
        ds6 = Mock()
        ds6.id = 6
        ds6.created_at = datetime(2025, 10, 31)
        meta6 = Mock()
        meta6.title = "Sigma dataset"
        meta6.description = "Nuclear fusion"
        meta6.tags = "physics,history"
        meta6.publication_type = PublicationType.DATA_PAPER
        author6 = Mock()
        author6.name = "J. Robert Oppenheimer"
        author6.affiliation = "Caltech"
        author6.orcid = "0000-0000-0000-0002"
        meta6.authors = [author6]
        ds6.ds_meta_data = meta6
        datasets.append(ds6)

        return datasets

    def test_filter_by_text_query_title(self, explore_service, sample_datasets):
        """Test filtering by title"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[0]]
            
            results = explore_service.filter(query="alpha")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Alpha dataset"

    def test_filter_by_text_query_description(self, explore_service, sample_datasets):
        """Test filtering by description"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[5]]
            
            results = explore_service.filter(query="Nuclear")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Sigma dataset"

    def test_filter_by_text_query_author_name(self, explore_service, sample_datasets):
        """Test filtering by author name"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[5]]
            
            results = explore_service.filter(query="Oppenheimer")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Sigma dataset"

    def test_filter_by_text_query_author_affiliation(self, explore_service, sample_datasets):
        """Test filtering by author affiliation"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[3]]
            
            results = explore_service.filter(query="Vienna")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Epsilon dataset"

    def test_filter_by_text_query_author_orcid(self, explore_service, sample_datasets):
        """Test filtering by author ORCID"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[2]]
            
            results = explore_service.filter(query="0000-0000-0000-0005")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Gamma dataset"

    def test_filter_by_text_query_tags(self, explore_service, sample_datasets):
        """Test filtering by tags"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[4], sample_datasets[5]]
            
            results = explore_service.filter(query="history")
            assert len(results) == 2
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Delta dataset" in titles
            assert "Sigma dataset" in titles

    def test_filter_by_date_after(self, explore_service, sample_datasets):
        """Test filtering by date after"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[5]]
            
            results = explore_service.filter(date_after="2025-01-01")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Sigma dataset"

    def test_filter_by_date_before(self, explore_service, sample_datasets):
        """Test filtering by date before"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[0], sample_datasets[1]]
            
            results = explore_service.filter(date_before="2024-02-01")
            assert len(results) == 2
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Alpha dataset" in titles
            assert "Beta dataset" in titles

    def test_filter_by_date_range(self, explore_service, sample_datasets):
        """Test filtering by date range"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = sample_datasets[:5]
            
            results = explore_service.filter(date_after="2024-01-01", date_before="2024-12-31")
            assert len(results) == 5
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Alpha dataset" in titles
            assert "Beta dataset" in titles
            assert "Gamma dataset" in titles
            assert "Epsilon dataset" in titles
            assert "Delta dataset" in titles
            assert "Sigma dataset" not in titles

    def test_filter_by_author_multiple(self, explore_service, sample_datasets):
        """Test filtering by author with multiple results"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[0], sample_datasets[1]]
            
            results = explore_service.filter(author="John Doe")
            assert len(results) == 2
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Alpha dataset" in titles
            assert "Beta dataset" in titles

    def test_filter_by_author_single(self, explore_service, sample_datasets):
        """Test filtering by author with single result"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[3]]
            
            results = explore_service.filter(author="Hans Landa")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Epsilon dataset"

    def test_filter_by_tags_single(self, explore_service, sample_datasets):
        """Test filtering by single tag"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = sample_datasets[:4]
            
            results = explore_service.filter(tags=["geo"])
            assert len(results) == 4
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Alpha dataset" in titles
            assert "Beta dataset" in titles
            assert "Gamma dataset" in titles
            assert "Epsilon dataset" in titles

    def test_filter_by_tags_multiple(self, explore_service, sample_datasets):
        """Test filtering by multiple tags"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[4], sample_datasets[5]]
            
            results = explore_service.filter(tags=["history", "art"])
            assert len(results) == 2
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Delta dataset" in titles
            assert "Sigma dataset" in titles

    def test_filter_by_publication_type_single(self, explore_service, sample_datasets):
        """Test filtering by single publication type"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = [sample_datasets[5]]
            
            results = explore_service.filter(publication_type="data_paper")
            assert len(results) == 1
            assert results[0].ds_meta_data.title == "Sigma dataset"

    def test_filter_by_publication_type_multiple(self, explore_service, sample_datasets):
        """Test filtering by journal article publication type"""
        with patch.object(explore_service.repository, "filter") as mock_filter:
            mock_filter.return_value = sample_datasets[:5]
            
            results = explore_service.filter(publication_type="journal_article")
            assert len(results) == 5
            titles = [ds.ds_meta_data.title for ds in results]
            assert "Alpha dataset" in titles
            assert "Beta dataset" in titles
            assert "Gamma dataset" in titles
            assert "Epsilon dataset" in titles
            assert "Delta dataset" in titles
            assert "Sigma dataset" not in titles
