from app import db
from app.modules.auth.models import Role, User
from app.modules.profile.models import UserProfile
from app.modules.dataset.models import DSDownloadRecord


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
            DSDownloadRecord.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            return True
        except Exception as exc:
            db.session.rollback()
            raise exc

    def get_all_roles(self):
        return Role.query.filter(Role.name.notin_(["user", "guest"])).order_by(Role.name).all()

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

    def create_user(self, form):
        if User.query.filter_by(email=form.email.data).first():
            return False, "Email already exists."

        try:
            new_user = User(email=form.email.data)
            new_user.set_password("contras3nya")

            db.session.add(new_user)
            db.session.flush()

            profile = UserProfile(
                user_id=new_user.id,
                name=form.name.data,
                surname=form.surname.data,
                orcid=form.orcid.data,
                affiliation=form.affiliation.data,
            )
            db.session.add(profile)

            base_user_role = Role.query.filter_by(name="user").first()
            if base_user_role:
                new_user.add_role(base_user_role)

            selected_roles_ids = form.roles.data
            if selected_roles_ids:
                roles_to_add = Role.query.filter(Role.id.in_(selected_roles_ids)).all()
                for role in roles_to_add:
                    new_user.add_role(role)

            db.session.commit()
            return True, "User created successfully."

        except Exception as exc:
            db.session.rollback()
            return False, str(exc)
