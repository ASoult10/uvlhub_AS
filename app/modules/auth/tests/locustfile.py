from locust import HttpUser, TaskSet, task, between

from core.environment.host import get_host_for_locust_testing
from core.locust.common import fake, get_csrf_token
import random
import re


class SignupBehavior(TaskSet):
    def on_start(self):
        self.signup()

    @task
    def signup(self):
        response = self.client.get("/signup")
        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/signup", data={"email": fake.email(), "password": fake.password(), "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Signup failed: {response.status_code}")


class LoginBehavior(TaskSet):
    def on_start(self):
        self.ensure_logged_out()
        self.login()

    @task
    def ensure_logged_out(self):
        response = self.client.get("/logout")
        if response.status_code != 200:
            print(f"Logout failed or no active session: {response.status_code}")

    @task
    def login(self):
        response = self.client.get("/login")
        if response.status_code != 200 or "Login" not in response.text:
            print("Already logged in or unexpected response, redirecting to logout")
            self.ensure_logged_out()
            response = self.client.get("/login")

        csrf_token = get_csrf_token(response)

        response = self.client.post(
            "/login", data={"email": "user1@example.com", "password": "1234", "csrf_token": csrf_token}
        )
        if response.status_code != 200:
            print(f"Login failed: {response.status_code}")

class DatasetCommentsBehavior(TaskSet):
    """
    Comportamiento de usuario para probar bajo carga:
    - Listado de comentarios de un dataset
    - Creación de comentarios
    - Moderación de comentarios
    """

    def on_start(self):
        """
        Al iniciar el usuario virtual:
        - Hacer login
        - Obtener un dataset_id válido desde /dataset/list
        """
        self.dataset_id = None
        self.last_comment_id = None

        self.login()
        self.dataset_id = self.get_dataset_id()

        if not self.dataset_id:
            print("No dataset_id found; some tasks will be skipped.")

    # ----------- Helpers -----------

    def login(self):
        """
        Login como user1@example.com / 1234 usando CSRF, igual que en locust de auth.
        """
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
        """
        Intenta obtener el ID de un dataset de /dataset/list (lista 'My datasets').
        Busca el primer enlace /dataset/download/<id>.
        """
        response = self.client.get("/dataset/list")
        if response.status_code != 200:
            print(f"[comments] Failed to load /dataset/list: {response.status_code}")
            # Fallback: intenta con 1, que suele existir en entorno seed
            return 1

        match = re.search(r"/dataset/download/(\d+)", response.text)
        if match:
            ds_id = int(match.group(1))
            # print(f"[comments] Using dataset_id={ds_id}")
            return ds_id

        print("[comments] Could not find dataset_id in /dataset/list HTML, using dataset_id=1 as fallback")
        return 1

    # ----------- Tasks -----------

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
            # Consideramos éxito tanto 200 como 201
            if response.status_code not in (200, 201):
                print("[comments] Failed to create comment, status:", response.status_code)
                print("[comments] Body:", response.text[:200])
                response.failure(f"Failed to create comment: {response.status_code}")
                return

            # Intentar guardar el id del comentario para moderarlo luego
            try:
                data = response.json()
                comment_id = data.get("id")
                if comment_id:
                    self.last_comment_id = comment_id
            except Exception as e:
                # Si no es JSON (por ejemplo, HTML), solo lo dejamos logueado
                print("[comments] Error parsing JSON when creating comment:", e)
                print("[comments] Body:", response.text[:200])

    @task(1)
    def moderate_comment(self):
        """
        Modera el último comentario creado.
        POST /dataset/<dataset_id>/comments/<comment_id>/moderate
        - action: hide/show/delete
        Nota: si el usuario no es owner ni admin, la API puede devolver 403 (aceptable en esta prueba).
        """
        if not self.dataset_id or not self.last_comment_id:
            # Nada que moderar aún
            return

        action = random.choice(["hide", "show", "delete"])

        with self.client.post(
            f"/dataset/{self.dataset_id}/comments/{self.last_comment_id}/moderate",
            json={"action": action},
            name="Moderate Dataset Comment",
            catch_response=True,
        ) as response:
            # 200 -> moderación OK
            # 403 -> usuario sin permisos (esperable si no es owner/admin)
            if response.status_code not in (200, 403):
                response.failure(f"Unexpected status moderating comment: {response.status_code}")

class AuthUser(HttpUser):
    tasks = [SignupBehavior, LoginBehavior]
    min_wait = 5000
    max_wait = 9000
    host = get_host_for_locust_testing()

class DatasetCommentsUser(HttpUser):
    """
    Usuario de Locust para probar comentarios de datasets.
    
    Ejemplo de ejecución:
        locust -f app/modules/dataset/tests/locustfile_comments.py DatasetCommentsUser
    """
    tasks = [DatasetCommentsBehavior]
    wait_time = between(3, 7)  # similar a otros tests: 3-7s entre tareas
    host = get_host_for_locust_testing()
