from locust import HttpUser, task, between


class ExploreModuleResponse(HttpUser):
    wait_time = between(1, 5)

    @task
    def load_explore(self):
        response = self.client.get("/explore")
        if response.status_code != 200:
            print(f"[explore] Fallo al cargar /explore: {response.status_code}")
