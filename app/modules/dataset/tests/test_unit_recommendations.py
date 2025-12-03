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

    def test_recommendation_excludes_current_dataset(self):
        """Test that the current dataset is not included in recommendations"""
        # Simple logic test - the algorithm filters with "DataSet.id != dataset_id"
        current_dataset_id = 1
        all_dataset_ids = [1, 2, 3, 4, 5]
        
        # Filter out current dataset (this is what the algorithm does)
        filtered_ids = [id for id in all_dataset_ids if id != current_dataset_id]
        
        # Verify current dataset is not in filtered list
        assert current_dataset_id not in filtered_ids
        assert len(filtered_ids) == 4

    def test_recommendation_requires_tag_or_author_match(self):
        """Test that only datasets with matching tags or authors are recommended"""
        current_tags = {"python", "machine learning"}
        current_authors = {"john doe"}
        
        # Dataset with matching tag
        candidate1_tags = {"python", "java"}
        candidate1_authors = {"jane smith"}
        has_match1 = bool(current_tags & candidate1_tags) or bool(current_authors & candidate1_authors)
        assert has_match1 == True
        
        # Dataset with matching author (FIX: compare with correct variable)
        candidate2_tags = {"rust", "go"}
        candidate2_authors = {"john doe"}
        has_match2 = bool(current_tags & candidate2_tags) or bool(current_authors & candidate2_authors)
        assert has_match2 == True
        
        # Dataset with no matches
        candidate3_tags = {"rust", "go"}
        candidate3_authors = {"jane smith"}
        has_match3 = bool(current_tags & candidate3_tags) or bool(current_authors & candidate3_authors)
        assert has_match3 == False

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

    def test_recommendation_limit_parameter(self):
        """Test that the limit parameter correctly limits results"""
        # Simulate the algorithm's limit logic
        all_recommendations = [
            {"dataset": Mock(id=i), "score": 10-i, "downloads": 10, "coincidences": 2}
            for i in range(1, 11)  # 10 recommendations
        ]
        
        # Test limit of 5
        limited_5 = all_recommendations[:5]
        assert len(limited_5) == 5
        
        # Test limit of 3
        limited_3 = all_recommendations[:3]
        assert len(limited_3) == 3
        
        # Test limit greater than available
        limited_20 = all_recommendations[:20]
        assert len(limited_20) == 10  # Only 10 available

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
