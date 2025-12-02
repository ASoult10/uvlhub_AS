from app.modules.auth.models import User
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder


class AuthSeeder(BaseSeeder):

    priority = 1  # Higher priority

    def run(self):

        # Seeding users
        users = [
            User(email="user1@example.com", password="1234", user_secret= "2345"),
            User(email="user2@example.com", password="1234", user_secret= "23467"),
        ]

        #Seeding roles
        roles = [
            Role(name='admin', description='Full system administrator'),
            Role(name='curator', description='Content curator'),
            Role(name='user', description='Standard authenticated user'),
            Role(name='guest', description='Read-only guest'),
        ]

        # Verificar qué roles ya existen para no duplicar
        existing = {r.name for r in Role.query.all()}
        roles_to_create = []
        for role in roles:
            if role.name not in existing:
                roles_to_create.append(role)

        if roles_to_create:
            seeded_roles = self.seed(roles_to_create)

        # Inserted users with their assigned IDs are returned by `self.seed`.
        seeded_users = self.seed(users)

        # Create profiles for each user inserted.
        user_profiles = []
        names = [("John", "Doe"), ("Jane", "Doe")]

        for user, name in zip(seeded_users, names):
            profile_data = {
                "user_id": user.id,
                "orcid": "",
                "affiliation": "Some University",
                "name": name[0],
                "surname": name[1],
            }
            user_profile = UserProfile(**profile_data)
            user_profiles.append(user_profile)

        # Seeding user profiles
        self.seed(user_profiles)
