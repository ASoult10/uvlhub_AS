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
