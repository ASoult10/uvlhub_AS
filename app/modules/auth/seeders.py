from app.modules.auth.models import Permission, Role, User
from app.modules.profile.models import UserProfile
from core.seeders.BaseSeeder import BaseSeeder


class AuthSeeder(BaseSeeder):

    priority = 1  # Higher priority

    def run(self):

        # Seeding users
        users = [
            User(email="user1@example.com", password="1234", user_secret="2345"),
            User(email="user2@example.com", password="1234", user_secret="23467"),
        ]

        # Seeding roles
        roles = [
            Role(name="admin", description="Full system administrator"),
            Role(name="curator", description="Content curator"),
            Role(name="user", description="Standard authenticated user"),
            Role(name="guest", description="Read-only guest"),
        ]

        # Verificar qué roles ya existen para no duplicar
        existing = {r.name for r in Role.query.all()}
        roles_to_create = []
        for role in roles:
            if role.name not in existing:
                roles_to_create.append(role)

        if roles_to_create:
            self.seed(roles_to_create)

        # Reload roles
        admin_role = Role.query.filter_by(name="admin").first()
        curator_role = Role.query.filter_by(name="curator").first()
        user_role = Role.query.filter_by(name="user").first()
        guest_role = Role.query.filter_by(name="guest").first()

        # Seeding permissions TODO: define more permissions
        permissions = [
            # Define permissions here if needed
            Permission(name="manage_users", description="Can create, edit, delete users"),
            Permission(name="create_content", description="Can create new content"),
            Permission(name="edit_any_content", description="Can edit any content"),
            Permission(name="delete_any_content", description="Can delete any content"),
            Permission(name="edit_own_content", description="Can edit own content"),
            Permission(name="delete_own_content", description="Can delete own content"),
            Permission(name="create_api_keys", description="Can create API keys"),
        ]

        # Verificar qué permisos ya existen para no duplicar
        existing_perms = {p.name for p in Permission.query.all()}
        perms_to_create = []
        for perm in permissions:
            if perm.name not in existing_perms:
                perms_to_create.append(perm)

        if perms_to_create:
            self.seed(perms_to_create)

        # Reload permissions
        def perm(n):
            return Permission.query.filter_by(name=n).first()

        # Assign permissions to roles

        # Admin: (tiene todos los permisos)
        for p in Permission.query.all():
            if not admin_role.permissions.filter_by(name=p.name).first():
                admin_role.permissions.append(p)

        # Curator:
        # TODO: assign curator permissions

        # User permissions TODO: define user permissions

        # Guest permissions TODO: define guest permissions

        # Inserted users with their assigned IDs are returned by `self.seed`.
        seeded_users = self.seed(users)

        # Assign 'user' role to each seeded user
        user_role = Role.query.filter_by(name="user").first()

        for user in seeded_users:
            user.add_role(user_role)

        # Assign other roles
        admin_role = Role.query.filter_by(name="admin").first()
        curator_role = Role.query.filter_by(name="curator").first()

        seeded_users[0].add_role(admin_role)  # First user is admin
        seeded_users[1].add_role(curator_role)  # Second user is curator

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
