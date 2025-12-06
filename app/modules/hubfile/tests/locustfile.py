from locust import HttpUser, TaskSet, task

from core.environment.host import get_host_for_locust_testing


class HubfileBehavior(TaskSet):
    def on_start(self):
        self.index()

    @task
    def index(self):
        response = self.client.get("/hubfile")

        if response.status_code != 200:
            print(f"Hubfile index failed: {response.status_code}")


class SaveModelsBehavior(TaskSet):
    def on_start(self):
        self.client.post("/login", data={
            "email": "user1@example.com",
            "password": "1234"
        })

    @task(3)
    def listar_archivos_guardados(self):
        response = self.client.get("/hubfile/saved")

        if response.status_code != 200:
            print(f"Error al listar archivos guardados: {response.status_code}")

    @task(2)
    def agregar_archivo_guardado(self):
        response = self.client.post("/hubfile/save/1")

        if response.status_code not in [200, 302]:
            print(f"Error al agregar el archivo guardado: {response.status_code}")

    @task(2)
    def eliminar_archivo_guardado(self):
        response = self.client.post("/hubfile/unsave/1")

        if response.status_code not in [200, 302]:
            print(f"Error al eliminar el archivo guardado: {response.status_code}")

    @task(1)
    def comprobar_si_archivo_esta_guardado(self):
        response = self.client.get("/hubfile/is_saved/1")

        if response.status_code != 200:
            print(f"Error al comprobar si el archivo está guardado: {response.status_code}")

    @task(1)
    def probar_con_archivo_inexistente(self):
        response = self.client.post("/hubfile/save/99999")

        if response.status_code not in [404, 302, 200]:
            print(f"Archivo inexistente: {response.status_code}")


class HubfileUser(HttpUser):
    tasks = [HubfileBehavior, SaveModelsBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()
