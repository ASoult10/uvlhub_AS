from locust import HttpUser, TaskSet, task, between
from core.environment.host import get_host_for_locust_testing
from core.locust.common import get_csrf_token

EMAIL = "test@example.com"
PASSWORD = "test1234"
TOKEN_ID = 1

class TokenBehavior(TaskSet):
    def on_start(self):
        response = self.client.get("/login")
        csrf_token = get_csrf_token(response)
        
        self.client.post(
            "/login",
            data={
                "email": EMAIL,
                "password": PASSWORD,
                "csrf_token": csrf_token
            }
        )

    # /token/sessions
    @task(5)
    def view_sessions(self):
        response = self.client.get("/token/sessions")
        
        if response.status_code != 200:
            print(f"Sessions page failed: {response.status_code}")

    # /token/revoke/<int:token_id>
    @task(2)
    def revoke_single_token(self):
        response = self.client.get("/token/sessions")
        
        if response.status_code == 200:
            response = self.client.put(f"/token/revoke/{TOKEN_ID}")
            
            if response.status_code not in [200, 404]:
                print(f"Revoke token failed: {response.status_code}")

    # /token/revoke/all
    @task(1)
    def revoke_all_tokens(self):
        response = self.client.put("/token/revoke/all")
        
        if response.status_code != 200:
            print(f"Revoke all tokens failed: {response.status_code}")


class TokenUser(HttpUser):
    tasks = [TokenBehavior]
    wait_time = between(1, 3)
    host = get_host_for_locust_testing()