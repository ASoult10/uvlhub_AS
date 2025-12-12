from locust import HttpUser, TaskSet, between, task

from core.environment.host import get_host_for_locust_testing


class ProfileBehavior(TaskSet):
    """
    TaskSet for testing author profile views.
    """

    def on_start(self):
        """
        Called when a simulated user starts executing this TaskSet.
        Gets a valid user_id to test with.
        """
        self.user_id = self.get_valid_user_id()
        if not self.user_id:
            print("No valid user_id found; some tasks will be skipped.")

    def get_valid_user_id(self):
        """
        Gets a valid user_id from the homepage or explore page by extracting
        it from an author profile link.
        """
        # Try to get a user_id from the homepage
        response = self.client.get("/")
        if response.status_code == 200:
            # Look for profile links in the format /profile/{user_id}
            import re
            match = re.search(r'/profile/(\d+)', response.text)
            if match:
                return int(match.group(1))

        # If not found on homepage, try explore page
        response = self.client.get("/explore")
        if response.status_code == 200:
            import re
            match = re.search(r'/profile/(\d+)', response.text)
            if match:
                return int(match.group(1))

        # Default to user_id 1 if nothing found
        return 1

    @task(3)
    def view_author_profile(self):
        """
        Test viewing an author's profile page.
        This simulates the most common user behavior.
        Weight: 3 (executed more frequently)
        """
        if not self.user_id:
            return

        with self.client.get(
            f"/profile/{self.user_id}",
            catch_response=True,
            name="/profile/[user_id]"
        ) as response:
            if response.status_code == 200:
                # Verify that essential content is present
                if b"Datasets authored by" in response.content or b"datasets" in response.content:
                    response.success()
                else:
                    response.failure("Profile page loaded but missing expected content")
            elif response.status_code == 404:
                response.failure(f"User with id {self.user_id} not found (404)")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def view_different_author_profiles(self):
        """
        Test viewing different random author profiles.
        This simulates users browsing different authors.
        Weight: 1 (executed less frequently)
        """
        # Test with random user_ids (1-10)
        import random
        random_user_id = random.randint(1, 10)

        with self.client.get(
            f"/profile/{random_user_id}",
            catch_response=True,
            name="/profile/[random_user_id]"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 404:
                # 404 is acceptable for random user_ids that don't exist
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")

    @task(1)
    def view_nonexistent_profile(self):
        """
        Test viewing a profile that doesn't exist.
        This verifies proper 404 handling.
        Weight: 1
        """
        nonexistent_id = 99999

        with self.client.get(
            f"/profile/{nonexistent_id}",
            catch_response=True,
            name="/profile/[nonexistent]"
        ) as response:
            if response.status_code == 404:
                response.success()
            else:
                response.failure(f"Expected 404 for nonexistent user, got {response.status_code}")


class ProfileUser(HttpUser):
    """
    Simulated user that performs profile-related tasks.
    """
    tasks = [ProfileBehavior]
    wait_time = between(1, 3)  # Wait between 1 and 3 seconds between tasks
    host = get_host_for_locust_testing()
