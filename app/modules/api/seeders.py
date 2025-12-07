import os
from dotenv import load_dotenv
from core.seeders.BaseSeeder import BaseSeeder
from app import db
from app.modules.auth.models import User
from app.modules.api.models import ApiKey

load_dotenv()

class ApiKeysSeeder(BaseSeeder):
    priority = 100  
    
    def run(self):
        """Crea las API keys de Locust desde .env."""
        locust_key = os.getenv("LOCUST_API_KEY")
        locust_stats_key = os.getenv("LOCUST_API_KEY_STATS") or locust_key
        
        if not locust_key:
            print("Falta LOCUST_API_KEY en .env, saltando seeder de API keys")
            return
        
        user = User.query.filter_by(email="locust@local").first()
        if not user:
            user = User(email="locust@local", password="locust-pass")
            db.session.add(user)
            db.session.commit()
            print("Usuario locust@local creado")
        
        def ensure_key(value, name, scopes):
            if ApiKey.query.filter_by(key=value).first():
                print(f"Key ya existe: {name}")
                return
            api_key = ApiKey(key=value, user_id=user.id, name=name, scopes=scopes, is_active=True)
            db.session.add(api_key)
            db.session.commit()
            print(f"Key creada: {name}")
        
        ensure_key(locust_key, "Locust datasets", "read:datasets")
        if locust_stats_key:
            ensure_key(locust_stats_key, "Locust stats", "read:datasets,read:stats")