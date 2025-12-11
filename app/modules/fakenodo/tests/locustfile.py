from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing
import random


class FakenodoUser(HttpUser):
    """
    Versión actualizada del test de carga:
    - NO usa TaskSet (deprecated)
    - Usa wait_time moderno
    - Las tareas se ejecutan correctamente y aparecen en el ratio
    """

    host = get_host_for_locust_testing()
    wait_time = lambda self: random.uniform(5, 9)   # Sustituye min_wait/max_wait

    # -------------------------------------------------------
    # Inicio: comportamientos equivalentes a tu antiguo TaskSet
    # -------------------------------------------------------

    def on_start(self):
        self.created_ids = []
        self.index()   # Igual que antes

    # ---------------------- TAREAS -------------------------

    @task(1)
    def index(self):
        response = self.client.get("/fakenodo/api")
        if response.status_code != 200:
            print(f"Fakenodo API test failed: {response.status_code}")

    @task(2)
    def list_depositions(self):
        response = self.client.get("/fakenodo/api/deposit/depositions")
        if response.status_code == 200:
            deps = response.json().get("depositions", [])
            if deps:
                self.created_ids = [d["id"] for d in deps if "id" in d]

    @task(3)
    def create_deposition(self):
        meta = {"title": f"Test {random.randint(1,10000)}"}
        response = self.client.post("/fakenodo/api/deposit/depositions", json={"metadata": meta})
        if response.status_code == 201:
            dep = response.json()
            self.created_ids.append(dep["id"])

    @task(2)
    def get_deposition(self):
        if self.created_ids:
            dep_id = random.choice(self.created_ids)
            self.client.get(f"/fakenodo/api/deposit/depositions/{dep_id}")

    @task(2)
    def upload_file(self):
        if self.created_ids:
            dep_id = random.choice(self.created_ids)
            self.client.post(
                f"/fakenodo/api/deposit/depositions/{dep_id}/files",
                data={"filename": "file.txt"}
            )

    @task(2)
    def publish_deposition(self):
        if self.created_ids:
            dep_id = random.choice(self.created_ids)
            self.client.post(
                f"/fakenodo/api/deposit/depositions/{dep_id}/actions/publish"
            )

    @task(1)
    def delete_deposition(self):
        if self.created_ids:
            dep_id = self.created_ids.pop(0)
            response = self.client.delete(f"/fakenodo/api/deposit/depositions/{dep_id}", catch_response=True)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"Unexpected status code: {response.status_code}")



    @task(1)
    def error_cases(self):
        bad_id = 999999
        self.client.get(f"/fakenodo/api/deposit/depositions/{bad_id}")
        self.client.post(
            f"/fakenodo/api/deposit/depositions/{bad_id}/files",
            data={"filename": "file.txt"}
        )
        self.client.post(
            f"/fakenodo/api/deposit/depositions/{bad_id}/actions/publish"
        )
        self.client.delete(f"/fakenodo/api/deposit/depositions/{bad_id}")
