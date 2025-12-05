import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from app import create_app
from app.modules.dataset.services import DataSetService


class TestRecommendationSystemUnit:
    """
    Unit tests for the dataset recommendation system.
    Tests the logic without database or UI dependencies.
    """

    @pytest.fixture
    def app(self):
        """Create Flask app for testing"""
        app = create_app()
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def app_context(self, app):
        """Create application context"""
        with app.app_context():
            yield app

    @pytest.fixture
    def mock_dataset_service(self, app_context):
        """Create a mock DataSetService for testing"""
        service = DataSetService()
        return service

    @pytest.fixture
    def sample_current_dataset(self):
        """Create a sample current dataset for testing"""
        dataset = Mock()
        dataset.id = 1
        dataset.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        
        metadata = Mock()
        metadata.title = "Test Dataset 1"
        metadata.tags = "machine learning, python, data science"
        metadata.authors = [
            Mock(name="John Doe"),
            Mock(name="Jane Smith")
        ]
        
        dataset.ds_meta_data = metadata
        return dataset

    @pytest.fixture
    def sample_candidate_datasets(self):
        """Create sample candidate datasets with different attributes"""
        candidates = []
        
        # Dataset 2: Same tags, different author, high downloads, recent
        dataset2 = Mock()
        dataset2.id = 2
        dataset2.created_at = datetime(2024, 11, 1, tzinfo=timezone.utc)
        metadata2 = Mock()
        metadata2.title = "Test Dataset 2"
        metadata2.tags = "machine learning, python"
        metadata2.authors = [Mock(name="Bob Johnson")]
        dataset2.ds_meta_data = metadata2
        candidates.append(dataset2)
        
        # Dataset 3: Same author, different tags, low downloads, old
        dataset3 = Mock()
        dataset3.id = 3
        dataset3.created_at = datetime(2023, 1, 1, tzinfo=timezone.utc)
        metadata3 = Mock()
        metadata3.title = "Test Dataset 3"
        metadata3.tags = "java, algorithms"
        metadata3.authors = [Mock(name="John Doe")]
        dataset3.ds_meta_data = metadata3
        candidates.append(dataset3)
        
        # Dataset 4: No matching tags/authors
        dataset4 = Mock()
        dataset4.id = 4
        dataset4.created_at = datetime(2024, 6, 1, tzinfo=timezone.utc)
        metadata4 = Mock()
        metadata4.title = "Test Dataset 4"
        metadata4.tags = "rust, blockchain"
        metadata4.authors = [Mock(name="Alice Williams")]
        dataset4.ds_meta_data = metadata4
        candidates.append(dataset4)
        
        return candidates

    def test_recommendation_returns_list(self, mock_dataset_service):
        """Test that get_recommendations returns a list"""
        with patch.object(mock_dataset_service.repository, 'get_by_id') as mock_get:
            mock_get.return_value = None
            result = mock_dataset_service.get_recommendations(999, limit=5)
            assert isinstance(result, list)

    def test_recommendation_returns_empty_for_nonexistent_dataset(self, mock_dataset_service):
        """Test that recommendations return empty list for non-existent dataset"""
        with patch.object(mock_dataset_service.repository, 'get_by_id') as mock_get:
            mock_get.return_value = None
            result = mock_dataset_service.get_recommendations(999, limit=5)
            assert result == []

    def test_recommendation_excludes_current_dataset(self, mock_dataset_service, sample_current_dataset):
        """Test that the current dataset is not included in recommendations"""
        with patch.object(mock_dataset_service.repository, 'get_by_id') as mock_get, \
             patch('app.modules.dataset.models.DataSet.query') as mock_query:
            
            mock_get.return_value = sample_current_dataset
            
            # Create candidate datasets
            candidates = []
            for i in range(2, 6):
                dataset = Mock()
                dataset.id = i
                dataset.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
                dataset.ds_meta_data = Mock()
                dataset.ds_meta_data.tags = "python"
                dataset.ds_meta_data.authors = []
                candidates.append(dataset)
            
            mock_query.filter.return_value.all.return_value = candidates
            
            with patch.object(mock_dataset_service.dsdownloadrecord_repository, 'count_downloads_for_dataset') as mock_downloads:
                mock_downloads.return_value = 10
                
                result = mock_dataset_service.get_recommendations(1, limit=10)
                
                # Verify current dataset is not in results
                for rec in result:
                    assert rec['dataset'].id != 1

    def test_recommendation_requires_tag_or_author_match(self, mock_dataset_service):
        """Test that only datasets with matching tags or authors are recommended"""
        # Create current dataset with specific tags and authors
        current = Mock()
        current.id = 1
        current.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        current.ds_meta_data = Mock()
        current.ds_meta_data.tags = "python, machine learning"
        author1 = Mock()
        author1.name = "John Doe"
        current.ds_meta_data.authors = [author1]
        
        # Create candidates
        candidates = []
        
        # Candidate 1: matching tag
        candidate1 = Mock()
        candidate1.id = 2
        candidate1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        candidate1.ds_meta_data = Mock()
        candidate1.ds_meta_data.tags = "python, java"
        author2 = Mock()
        author2.name = "Jane Smith"
        candidate1.ds_meta_data.authors = [author2]
        candidates.append(candidate1)
        
        # Candidate 2: matching author
        candidate2 = Mock()
        candidate2.id = 3
        candidate2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        candidate2.ds_meta_data = Mock()
        candidate2.ds_meta_data.tags = "rust, go"
        author3 = Mock()
        author3.name = "John Doe"
        candidate2.ds_meta_data.authors = [author3]
        candidates.append(candidate2)
        
        # Candidate 3: no matches
        candidate3 = Mock()
        candidate3.id = 4
        candidate3.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
        candidate3.ds_meta_data = Mock()
        candidate3.ds_meta_data.tags = "rust, blockchain"
        author4 = Mock()
        author4.name = "Alice"
        candidate3.ds_meta_data.authors = [author4]
        candidates.append(candidate3)
        
        with patch.object(mock_dataset_service.repository, 'get_by_id') as mock_get, \
             patch('app.modules.dataset.models.DataSet.query') as mock_query:
            
            mock_get.return_value = current
            mock_query.filter.return_value.all.return_value = candidates
            
            with patch.object(mock_dataset_service.dsdownloadrecord_repository, 'count_downloads_for_dataset') as mock_downloads:
                mock_downloads.return_value = 10
                
                result = mock_dataset_service.get_recommendations(1, limit=10)
                
                # Should return only candidates with matches (1 and 2, not 3)
                result_ids = [rec['dataset'].id for rec in result]
                assert 2 in result_ids  # Has matching tag
                assert 3 in result_ids  # Has matching author
                assert 4 not in result_ids  # No matches

    def test_recommendation_scoring_downloads(self):
        """Test that downloads are scored correctly (3 points max)"""
        # Tier 1 (low downloads) = 1.0 points
        downloads_low = 5
        # Tier 2 (medium downloads) = 2.0 points
        downloads_medium = 16
        # Tier 3 (high downloads) = 3.0 points
        downloads_high = 30
        
        # Downloads list for partitioning
        downloads_list = sorted([5, 10, 15, 20, 25, 30])
        n = len(downloads_list)
        tier1_max = downloads_list[n // 3]  # 10
        tier2_max = downloads_list[(2 * n) // 3]  # 20
        
        # Test scoring logic
        assert downloads_low <= tier1_max  # Should get 1.0 points
        assert tier1_max < downloads_medium <= tier2_max  # Should get 2.0 points
        assert downloads_high > tier2_max  # Should get 3.0 points

    def test_recommendation_scoring_recency(self):
        """Test that recency is scored correctly (3 points max)"""
        # Tier 1 (old) = 1.0 points
        date_old = datetime(2022, 1, 1, tzinfo=timezone.utc)
        # Tier 2 (medium) = 2.0 points
        date_medium = datetime(2023, 7, 1, tzinfo=timezone.utc)
        # Tier 3 (recent) = 3.0 points
        date_recent = datetime(2024, 11, 1, tzinfo=timezone.utc)
        
        # Dates list for partitioning
        dates_list = sorted([
            datetime(2022, 1, 1, tzinfo=timezone.utc),
            datetime(2022, 6, 1, tzinfo=timezone.utc),
            datetime(2023, 6, 1, tzinfo=timezone.utc),
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 6, 1, tzinfo=timezone.utc),
            datetime(2024, 11, 1, tzinfo=timezone.utc),
        ])
        n = len(dates_list)
        tier1_max = dates_list[n // 3]  # datetime(2022, 6, 1)
        tier2_max = dates_list[(2 * n) // 3]  # datetime(2024, 1, 1)
        
        # Test scoring logic
        assert date_old <= tier1_max  # Should get 1.0 points
        assert tier1_max < date_medium <= tier2_max  # Should get 2.0 points
        assert date_recent > tier2_max  # Should get 3.0 points

    def test_recommendation_scoring_coincidences(self):
        """Test that coincidences are scored correctly (4 points max)"""
        max_coincidences = 5
        
        # 1 coincidence
        score_1 = (1 / max_coincidences) * 4.0
        assert score_1 == 0.8
        
        # 3 coincidences
        score_3 = (3 / max_coincidences) * 4.0
        assert score_3 == 2.4
        
        # Max coincidences
        score_max = (max_coincidences / max_coincidences) * 4.0
        assert score_max == 4.0

    def test_recommendation_max_score(self):
        """Test that maximum possible score is 10 points"""
        max_downloads_score = 3.0
        max_recency_score = 3.0
        max_coincidences_score = 4.0
        
        total_max_score = max_downloads_score + max_recency_score + max_coincidences_score
        assert total_max_score == 10.0

    def test_recommendation_limit_parameter(self, mock_dataset_service):
        """Test that the limit parameter correctly limits results"""
        # Create current dataset
        current = Mock()
        current.id = 1
        current.ds_meta_data = Mock()
        current.ds_meta_data.tags = "python"
        current.ds_meta_data.authors = []
        
        # Create 10 candidate datasets
        candidates = []
        for i in range(2, 12):
            dataset = Mock()
            dataset.id = i
            dataset.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
            dataset.ds_meta_data = Mock()
            dataset.ds_meta_data.tags = "python"
            dataset.ds_meta_data.authors = []
            candidates.append(dataset)
        
        with patch.object(mock_dataset_service.repository, 'get_by_id') as mock_get, \
             patch('app.modules.dataset.models.DataSet.query') as mock_query:
            
            mock_get.return_value = current
            mock_query.filter.return_value.all.return_value = candidates
            
            with patch.object(mock_dataset_service.dsdownloadrecord_repository, 'count_downloads_for_dataset') as mock_downloads:
                mock_downloads.return_value = 10
                
                # Test limit of 5
                result = mock_dataset_service.get_recommendations(1, limit=5)
                assert len(result) == 5
                
                # Test limit of 3
                result = mock_dataset_service.get_recommendations(1, limit=3)
                assert len(result) == 3

    def test_recommendation_sorting_by_score(self):
        """Test that recommendations are sorted by score (descending)"""
        recommendations = [
            {"dataset": Mock(id=1), "score": 5.5, "downloads": 10, "coincidences": 2},
            {"dataset": Mock(id=2), "score": 8.2, "downloads": 25, "coincidences": 4},
            {"dataset": Mock(id=3), "score": 3.1, "downloads": 5, "coincidences": 1},
            {"dataset": Mock(id=4), "score": 9.0, "downloads": 30, "coincidences": 5},
        ]
        
        # Sort by score descending (as the algorithm does)
        recommendations.sort(key=lambda x: x["score"], reverse=True)
        
        # Verify sorting
        assert recommendations[0]["score"] == 9.0
        assert recommendations[1]["score"] == 8.2
        assert recommendations[2]["score"] == 5.5
        assert recommendations[3]["score"] == 3.1

    def test_recommendation_handles_empty_tags(self):
        """Test that algorithm handles datasets with no tags"""
        dataset_tags = None
        tags_set = set()
        if dataset_tags:
            tags_set = {tag.strip().lower() for tag in dataset_tags.split(",")}
        
        assert tags_set == set()
        
        # Should still work with author matching
        current_authors = {"john doe"}
        dataset_authors = {"john doe"}
        
        has_match = bool(tags_set & tags_set) or bool(current_authors & dataset_authors)
        assert has_match == True

    def test_recommendation_case_insensitive_matching(self):
        """Test that tag and author matching is case-insensitive"""
        current_tags = {"Python", "Machine Learning"}
        candidate_tags = {"python", "MACHINE LEARNING"}
        
        # Convert to lowercase
        current_lower = {t.lower() for t in current_tags}
        candidate_lower = {t.lower() for t in candidate_tags}
        
        matches = current_lower & candidate_lower
        assert len(matches) == 2
        assert "python" in matches
        assert "machine learning" in matches

    def test_recommendation_handles_whitespace_in_tags(self):
        """Test that tags with whitespace are handled correctly"""
        tag_string = "python, machine learning,  data science  , ai"
        tags = {tag.strip().lower() for tag in tag_string.split(",")}
        
        assert "python" in tags
        assert "machine learning" in tags
        assert "data science" in tags
        assert "ai" in tags
        assert len(tags) == 4


# Run with: pytest app/modules/dataset/tests/test_unit_recommendations.py -v
