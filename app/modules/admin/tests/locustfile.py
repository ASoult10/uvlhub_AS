from locust import HttpUser, task, between
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token
from faker import Faker

fake = Faker()

class AdminUserBehavior(HttpUser):
    # Simulamos un usuario que espera entre 1 y 5 segundos entre acciones
    wait_time = between(1, 5)
    host = get_host_for_locust_testing()

    # Credenciales del Admin
    email = "user1@example.com"
    password = "1234"

    def on_start(self):
        """
        Se ejecuta una vez cuando el usuario simulado "nace".
        Aquí realizamos el login para obtener la sesión de administrador.
        """
        self.login()

    def login(self):
        # 1. GET al login para obtener la cookie de sesión y el token CSRF
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)

        # 2. POST con las credenciales
        response = self.client.post("/login", data={
            "email": self.email,
            "password": self.password,
            "csrf_token": csrf_token
        })
        
        if response.status_code != 200:
            print(f"Admin Login failed: {response.status_code}")
        else:
            print("Admin Logged in successfully")

    @task(4)
    def list_users(self):
        """
        Tarea frecuente (peso 4): Listar usuarios.
        Es la acción más común que hará un admin.
        """
        self.client.get("/users")

    @task(2)
    def view_specific_user(self):
        """
        Tarea media (peso 2): Ver detalles de un usuario.
        Usamos el ID 1 (el propio admin) para asegurar que existe y no dar 404.
        """
        self.client.get("/users/1")

    @task(1)
    def create_user_form_access(self):
        """
        Tarea baja (peso 1): Solo entrar al formulario de crear usuario (GET).
        Esto carga el servidor pero no escribe en la base de datos.
        """
        self.client.get("/users/create")

    @task(1)
    def create_user_action(self):
        """
        Tarea baja (peso 1): Crear un usuario realmente (POST).
        Generamos datos falsos para evitar errores de duplicidad.
        """
        # 1. Primero hacemos GET para robar el CSRF token de la página de creación
        response = self.client.get("/users/create")
        csrf_token = get_csrf_token(response)

        # 2. Generamos datos aleatorios
        random_email = fake.email()
        random_name = fake.first_name()
        random_surname = fake.last_name()
        
        # 3. Enviamos el formulario tal cual lo tienes definido en el HTML
        # Nota: 'roles' es un select multiple. Enviamos '1' asumiendo que es un ID válido de rol.
        self.client.post("/users/create", data={
            "csrf_token": csrf_token,
            "email": random_email,
            "name": random_name,
            "surname": random_surname,
            "orcid": "0000-0000-0000-0000",
            "affiliation": "Locust Test University",
            "roles": "1",  # Asumiendo ID 1 para algún rol
            "submit": "Submit" # A veces necesario si el backend chequea qué botón se pulsó
        })