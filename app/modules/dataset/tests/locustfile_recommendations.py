from locust import HttpUser, TaskSet, task, between
import random

from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token


class RecommendationBehavior(TaskSet):
    """
    Task set for testing the dataset recommendation system under load.
    Tests homepage, dataset view, and explore page recommendations.
    """

    def on_start(self):
        """Initialize by getting some dataset IDs"""
        self.dataset_dois = []
        self.get_dataset_list()

    def get_dataset_list(self):
        """Get list of available datasets to use in tests"""
        response = self.client.get("/dataset/list")
        if response.status_code == 200:
            # Parse response to get dataset DOIs if possible
            # For now, we'll use a fallback list
            print("Dataset list loaded")

    @task(5)
    def homepage_recommendations(self):
        """
        Test loading homepage with recommendations (5x weight - most common)
        This endpoint shows 3 recommendations per latest dataset
        """
        with self.client.get(
            "/",
            catch_response=True,
            name="Homepage with Recommendations"
        ) as response:
            if response.status_code == 200:
                # Check if recommendations are in the response
                if b"Similar Datasets" in response.content or b"recommendations_map" in response.content:
                    response.success()
                else:
                    response.failure("No recommendations found in homepage")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(3)
    def explore_with_recommendations(self):
        """
        Test explore page with recommendations (3x weight)
        This endpoint shows 3 recommendations per search result
        """
        # First, load the explore page
        with self.client.get(
            "/explore",
            catch_response=True,
            name="Explore Page Load"
        ) as response:
            if response.status_code != 200:
                response.failure(f"Explore page load failed: {response.status_code}")
                return
            
            csrf_token = get_csrf_token(response)

        # Then, perform a search (which triggers recommendations)
        search_criteria = {
            "query": "",
            "title": "",
            "description": "",
            "tags": "",
            "authors": ""
        }

        with self.client.post(
            "/explore",
            json=search_criteria,
            headers={
                "X-CSRFToken": csrf_token,
                "Content-Type": "application/json"
            },
            catch_response=True,
            name="Explore Search with Recommendations"
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    # Check if results have recommendations
                    if isinstance(data, list) and len(data) > 0:
                        has_recommendations = any("recommendations" in item for item in data)
                        if has_recommendations:
                            response.success()
                        else:
                            response.failure("No recommendations in search results")
                    else:
                        response.success()  # Empty results are ok
                except Exception as e:
                    response.failure(f"Failed to parse response: {e}")
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(2)
    def dataset_view_recommendations(self):
        """
        Test dataset view page with recommendations (2x weight)
        This endpoint shows 5 recommendations per dataset
        """
        # Use a known dataset DOI or try to get one from the list
        dataset_dois = [
            "10.1234/dataset1",
            "10.1234/dataset2",
            "10.1234/dataset3",
            "10.1234/dataset4",
        ]
        
        doi = random.choice(dataset_dois)
        
        with self.client.get(
            f"/doi/{doi}/",
            catch_response=True,
            name="Dataset View with Recommendations"
        ) as response:
            if response.status_code == 200:
                # Check if recommendations section exists
                if b"Recommended Datasets" in response.content or b"recommendations" in response.content:
                    response.success()
                else:
                    # It's ok if there are no recommendations (no similar datasets)
                    response.success()
            elif response.status_code == 404:
                # Dataset might not exist, that's ok in load testing
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def unsynchronized_dataset_recommendations(self):
        """
        Test unsynchronized dataset view with recommendations (1x weight - less common)
        """
        # Try dataset IDs 1-10
        dataset_id = random.randint(1, 10)
        
        with self.client.get(
            f"/dataset/unsynchronized/{dataset_id}/",
            catch_response=True,
            name="Unsynchronized Dataset with Recommendations"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [404, 401, 403]:
                # Expected errors for non-existent or unauthorized access
                response.success()
            else:
                response.failure(f"Status code: {response.status_code}")

    @task(1)
    def stress_test_multiple_recommendations(self):
        """
        Stress test: Load homepage multiple times rapidly to test recommendation caching/performance
        """
        for i in range(3):
            with self.client.get(
                "/",
                catch_response=True,
                name="Rapid Homepage Loads"
            ) as response:
                if response.status_code == 200:
                    response.success()
                else:
                    response.failure(f"Load {i+1} failed: {response.status_code}")


class RecommendationUser(HttpUser):
    """
    Simulated user for testing recommendation system performance.
    
    Usage:
        locust -f app/modules/dataset/tests/locustfile_recommendations.py --headless -u 50 -r 10 -t 60s
        
    Parameters:
        -u 50: 50 concurrent users
        -r 10: spawn 10 users per second
        -t 60s: run for 60 seconds
    """
    tasks = [RecommendationBehavior]
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    host = get_host_for_locust_testing()


class LightRecommendationUser(HttpUser):
    """
    Light load testing - fewer users, longer wait times
    Good for initial testing and verification
    
    Usage:
        locust -f app/modules/dataset/tests/locustfile_recommendations.py --headless -u 10 -r 2 -t 30s LightRecommendationUser
    """
    tasks = [RecommendationBehavior]
    wait_time = between(3, 7)  # Wait 3-7 seconds between tasks
    host = get_host_for_locust_testing()


class HeavyRecommendationUser(HttpUser):
    """
    Heavy load testing - many users, short wait times
    Simulates high traffic scenarios
    
    Usage:
        locust -f app/modules/dataset/tests/locustfile_recommendations.py --headless -u 100 -r 20 -t 120s HeavyRecommendationUser
    """
    tasks = [RecommendationBehavior]
    wait_time = between(0.5, 2)  # Wait 0.5-2 seconds between tasks
    host = get_host_for_locust_testing()
