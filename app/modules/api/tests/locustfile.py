import os
import random
import secrets
from dotenv import load_dotenv
from locust import HttpUser, task, between, LoadTestShape

load_dotenv()
LOCUST_API_KEY = os.getenv("LOCUST_API_KEY")
LOCUST_API_KEY_STATS = os.getenv("LOCUST_API_KEY_STATS", LOCUST_API_KEY)


class ApiUser(HttpUser):
    wait_time = between(1, 3)
    weight = 3

    def on_start(self):
        if not LOCUST_API_KEY:
            raise RuntimeError("Define LOCUST_API_KEY en .env")
        self.headers = {"X-API-Key": LOCUST_API_KEY}
        self.stats_headers = {"X-API-Key": LOCUST_API_KEY_STATS}

    @task(3)
    def get_dataset_by_id(self):
        dataset_id = random.randint(1, 100)
        with self.client.get(f"/api/datasets/id/{dataset_id}", headers=self.headers, catch_response=True,
                             name="/api/datasets/id/[id]") as r:
            r.success() if r.status_code in (200, 404) else r.failure(f"{r.status_code}")

    @task(2)
    def get_dataset_by_title(self):
        title = random.choice(["sample-dataset", "test-data", "research-project", "my-dataset"])
        with self.client.get(f"/api/datasets/title/{title}", headers=self.headers, catch_response=True,
                             name="/api/datasets/title/[title]") as r:
            r.success() if r.status_code in (200, 404) else r.failure(f"{r.status_code}")

    @task(5)
    def list_datasets(self):
        with self.client.get("/api/datasets", headers=self.headers, catch_response=True) as r:
            r.success() if r.status_code == 200 else r.failure(f"{r.status_code}")

    @task(4)
    def search_datasets(self):
        query = random.choice(["feature", "model", "dataset", "test", "sample"])
        page = random.randint(1, 3)
        per_page = random.choice([5, 10, 20])
        with self.client.get(f"/api/search?q={query}&page={page}&per_page={per_page}",
                             headers=self.headers, catch_response=True, name="/api/search") as r:
            r.success() if r.status_code == 200 else r.failure(f"{r.status_code}")

    @task(1)
    def get_stats(self):
        with self.client.get("/api/stats", headers=self.stats_headers, catch_response=True) as r:
            r.success() if r.status_code == 200 else r.failure(f"{r.status_code}")

    @task(1)
    def get_docs(self):
        with self.client.get("/api/docs", catch_response=True) as r:
            r.success() if r.status_code == 200 else r.failure(f"{r.status_code}")


class ApiUserWithoutKey(HttpUser):
    wait_time = between(2, 4)
    weight = 1

    @task(2)
    def access_without_key(self):
        with self.client.get("/api/datasets", catch_response=True) as r:
            r.success() if r.status_code == 401 else r.failure(f"{r.status_code}")

    @task(1)
    def access_with_invalid_key(self):
        headers = {"X-API-Key": "invalid_" + secrets.token_urlsafe(8)}
        with self.client.get("/api/datasets", headers=headers, catch_response=True) as r:
            r.success() if r.status_code == 403 else r.failure(f"{r.status_code}")


class RateLimitTester(HttpUser):
    wait_time = between(0.1, 0.5)
    weight = 1

    def on_start(self):
        if not LOCUST_API_KEY:
            raise RuntimeError("Define LOCUST_API_KEY en .env")
        self.headers = {"X-API-Key": LOCUST_API_KEY}

    @task
    def rapid_requests(self):
        with self.client.get("/api/datasets", headers=self.headers, catch_response=True) as r:
            r.success() if r.status_code in (200, 429) else r.failure(f"{r.status_code}")


class StepLoadShape(LoadTestShape):
    step_time = 30
    step_load = 10
    spawn_rate = 2
    time_limit = 300
    def tick(self):
        t = self.get_run_time()
        if t > self.time_limit:
            return None
        step = t // self.step_time
        return int((step + 1) * self.step_load), self.spawn_rate


class SpikeLoadShape(LoadTestShape):
    def tick(self):
        t = self.get_run_time()
        if t < 60:
            return 10, 2
        if t < 120:
            return 100, 10
        if t < 180:
            return 10, 2
        if t < 240:
            return 150, 15
        if t < 300:
            return 10, 2
        return None


class ConstantLoadShape(LoadTestShape):
    user_count = 50
    spawn_rate = 5
    time_limit = 600
    def tick(self):
        t = self.get_run_time()
        return (self.user_count, self.spawn_rate) if t < self.time_limit else None