from locust import HttpUser, TaskSet, task, between

from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token
import random
import re

class DatasetBehavior(TaskSet):
    def on_start(self):
        self.dataset()

    @task
    def dataset(self):
        response = self.client.get("/dataset/upload")
        get_csrf_token(response)

class DatasetCommentsBehavior(TaskSet):
    

    def on_start(self):
        
        self.dataset_id = None
        self.last_comment_id = None

        self.login()
        self.dataset_id = self.get_dataset_id()

        if not self.dataset_id:
            print("No dataset_id found; some tasks will be skipped.")

    

    def login(self):
        
        response = self.client.get("/login")
        if response.status_code != 200:
            print(f"[comments] GET /login failed: {response.status_code}")
            return

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login",
            data={
                "email": "user1@example.com",
                "password": "1234",
                "csrf_token": csrf_token,
            },
        )
        if response.status_code != 200:
            print(f"[comments] Login failed: {response.status_code}")

    def get_dataset_id(self):
        
        response = self.client.get("/dataset/list")
        if response.status_code != 200:
            print(f"[comments] Failed to load /dataset/list: {response.status_code}")
            
            return 1

        match = re.search(r"/dataset/download/(\d+)", response.text)
        if match:
            ds_id = int(match.group(1))

            return ds_id

        print("[comments] Could not find dataset_id in /dataset/list HTML, using dataset_id=1 as fallback")
        return 1

 

    @task(3)
    def list_comments(self):
        """
        Lista comentarios visibles de un dataset.
        GET /dataset/<dataset_id>/comments/
        """
        if not self.dataset_id:
            return

        with self.client.get(
            f"/dataset/{self.dataset_id}/comments/",
            name="List Dataset Comments",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Failed to list comments: {response.status_code}")

    @task(4)
    def create_comment(self):
        """
        Crea un nuevo comentario visible en el dataset.
        POST /dataset/<dataset_id>/comments/  (JSON)
        """
        if not self.dataset_id:
            return

        content = f"Load test comment: {fake.sentence(nb_words=6)}"

        with self.client.post(
            f"/dataset/{self.dataset_id}/comments/",
            json={"content": content},
            name="Create Dataset Comment",
            catch_response=True,
        ) as response:
            
            if response.status_code not in (200, 201):
                print("[comments] Failed to create comment, status:", response.status_code)
                print("[comments] Body:", response.text[:200])
                response.failure(f"Failed to create comment: {response.status_code}")
                return

            
            try:
                data = response.json()
                comment_id = data.get("id")
                if comment_id:
                    self.last_comment_id = comment_id
            except Exception as e:
                print("[comments] Error parsing JSON when creating comment:", e)
                print("[comments] Body:", response.text[:200])

    @task(1)
    def moderate_comment(self):
        
        if not self.dataset_id or not self.last_comment_id:
            
            return

        action = random.choice(["hide", "show", "delete"])

        with self.client.post(
            f"/dataset/{self.dataset_id}/comments/{self.last_comment_id}/moderate",
            json={"action": action},
            name="Moderate Dataset Comment",
            catch_response=True,
        ) as response:
            
            if response.status_code not in (200, 403):
                response.failure(f"Unexpected status moderating comment: {response.status_code}")


class DatasetUser(HttpUser):
    tasks = [DatasetBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()

class DatasetCommentsUser(HttpUser):
    
    tasks = [DatasetCommentsBehavior]
    wait_time = between(3, 7)  
    
    host = get_host_for_locust_testing()
