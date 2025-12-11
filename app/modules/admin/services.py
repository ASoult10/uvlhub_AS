from app import db
from app.modules.auth.models import Role, User
from app.modules.profile.models import UserProfile


class AdminService:
    def list_users(self):
        return User.query.order_by(User.id.desc()).all()

    def get_user(self, user_id: int):
        return User.query.filter_by(id=user_id).one_or_none()

    def delete_user(self, user_id: int):
        user = self.get_user(user_id)
        if not user:
            return False
        try:
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            raise exc

    def get_all_roles(self):
        return Role.query.filter(Role.name != "user").order_by(Role.name).all()

    def update_user(self, user_id, form):
        user = self.get_user(user_id)
        if not user:
            return False

        try:
            user.email = form.email.data

            if not user.profile:
                user.profile = UserProfile(user_id=user.id)
            user.profile.name = form.name.data
            user.profile.surname = form.surname.data
            user.profile.orcid = form.orcid.data
            user.profile.affiliation = form.affiliation.data

            user.roles = []
            base_user_role = Role.query.filter_by(name="user").first()
            if base_user_role:
                user.add_role(base_user_role)

            selected_roles = form.roles.data
            if selected_roles:
                roles_to_add = Role.query.filter(Role.id.in_(selected_roles)).all()
                for role in roles_to_add:
                    user.add_role(role)

            db.session.commit()
            return True

        except Exception as exc:
            db.session.rollback()
            raise exc

    def create_user(self, email: str, password: str, role_names=None, **profile_data):

        if not email or not password:
            raise ValueError("Email and password are required to create a user.")

        if role_names:
            roles_to_assign = Role.query.filter(Role.name.in_(role_names)).all()
        else:
            default_role = Role.query.filter_by(name="user").first()
            roles_to_assign = [default_role] if default_role else []

        try:
            user = User(email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.flush()  # To get user.id

            if profile_data:
                profile = UserProfile(user_id=user.id, **profile_data)
                db.session.add(profile)

                for key, value in profile_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)

            user.roles = roles_to_assign

            db.session.commit()
            return user
        except Exception as exc:
            db.session.rollback()
            raise exc

    def assign_role_to_user(self, user: User, role_name: str):
        role = db.session.query(Role).filter_by(name=role_name).first()
        if role:
            user.add_role(role)
            db.session.commit()
            return True
        return False

    def remove_role_from_user(self, user: User, role_name: str):
        role = db.session.query(Role).filter_by(name=role_name).first()
        if role:
            user.remove_role(role)
            db.session.commit()
            return True
        return False
