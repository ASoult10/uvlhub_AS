import pytest
from unittest.mock import MagicMock, patch
from flask import Flask
from flask_login import LoginManager
from app.modules.admin.services import AdminService

# ==========================================
# 1. TESTS DEL SERVICIO (Lógica de Negocio)
# ==========================================

class TestAdminService:
    
    @pytest.fixture
    def mock_db(self):
        with patch('app.modules.admin.services.db') as mock:
            yield mock

    @pytest.fixture
    def mock_user_model(self):
        with patch('app.modules.admin.services.User') as mock:
            yield mock

    @pytest.fixture
    def mock_role_model(self):
        with patch('app.modules.admin.services.Role') as mock:
            yield mock

    def test_list_users(self, mock_user_model):
        service = AdminService()
        mock_user_model.query.order_by.return_value.all.return_value = ['user1', 'user2']
        result = service.list_users()
        assert result == ['user1', 'user2']

    def test_delete_user_success(self, mock_db, mock_user_model):
        service = AdminService()
        user_mock = MagicMock()
        mock_user_model.query.filter_by.return_value.one_or_none.return_value = user_mock

        result = service.delete_user(1)

        assert result is True
        mock_db.session.delete.assert_called_with(user_mock)
        mock_db.session.commit.assert_called()

    def test_delete_user_not_found(self, mock_db, mock_user_model):
        service = AdminService()
        mock_user_model.query.filter_by.return_value.one_or_none.return_value = None

        result = service.delete_user(999)

        assert result is False
        mock_db.session.delete.assert_not_called()

    def test_delete_user_exception(self, mock_db, mock_user_model):
        service = AdminService()
        user_mock = MagicMock()
        mock_user_model.query.filter_by.return_value.one_or_none.return_value = user_mock
        mock_db.session.commit.side_effect = Exception("DB Error")

        with pytest.raises(Exception):
            service.delete_user(1)
        
        mock_db.session.rollback.assert_called()

    def test_create_user_success(self, mock_db, mock_user_model, mock_role_model):
        service = AdminService()
        form = MagicMock()
        form.email.data = "new@test.com"
        form.roles.data = [1]

        mock_user_model.query.filter_by.return_value.first.return_value = None
        new_user = MagicMock(id=10)
        mock_user_model.return_value = new_user
        mock_role_model.query.filter.return_value.all.return_value = [MagicMock()]

        success, msg = service.create_user(form)

        assert success is True
        mock_db.session.add.assert_called()
        mock_db.session.commit.assert_called()

    def test_create_user_duplicate_email(self, mock_db, mock_user_model):
        service = AdminService()
        form = MagicMock()
        form.email.data = "existe@test.com"
        mock_user_model.query.filter_by.return_value.first.return_value = MagicMock()

        success, msg = service.create_user(form)
        assert success is False
        assert "Email already exists" in msg

    def test_update_user_logic(self, mock_db, mock_user_model, mock_role_model):
        service = AdminService()
        form = MagicMock()
        form.email.data = "updated@test.com"
        form.roles.data = []

        user_mock = MagicMock()
        user_mock.profile = MagicMock()
        mock_user_model.query.filter_by.return_value.one_or_none.return_value = user_mock

        result = service.update_user(1, form)
        
        assert result is True
        assert user_mock.email == "updated@test.com"
        mock_db.session.commit.assert_called()

    def test_get_all_roles_excludes_defaults(self, mock_role_model):
        service = AdminService()
        service.get_all_roles()
        mock_role_model.query.filter.assert_called()

    def test_update_user_roles_logic(self, mock_db, mock_user_model, mock_role_model):
        service = AdminService()
        user_id = 1
        
        form = MagicMock()
        form.roles.data = [5, 6]
        
        user_mock = MagicMock()
        user_mock.roles = ["rol_viejo"] 
        mock_user_model.query.filter_by.return_value.one_or_none.return_value = user_mock
        
        base_role_mock = MagicMock(name="BaseRole")
        mock_role_model.query.filter_by.return_value.first.return_value = base_role_mock
        
        role_5 = MagicMock(id=5)
        role_6 = MagicMock(id=6)
        mock_role_model.query.filter.return_value.all.return_value = [role_5, role_6]

        service.update_user(user_id, form)

        assert user_mock.roles == []
        user_mock.add_role.assert_any_call(base_role_mock)
        user_mock.add_role.assert_any_call(role_5)
        user_mock.add_role.assert_any_call(role_6)
        mock_db.session.commit.assert_called()


# ==========================================
# 2. TESTS DE LAS RUTAS (Controladores)
# ==========================================

class TestAdminRoutes:
    
    @pytest.fixture(autouse=True)
    def mock_service_instance(self):
        with patch('app.modules.admin.routes.admin_service') as mock:
            yield mock

    @pytest.fixture(autouse=True)
    def mock_auth(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.is_active = True
        mock_user.id = 1
        mock_user.get_id.return_value = "1"
        mock_user.has_permission.return_value = True

        with patch('app.modules.admin.routes.current_user', new=mock_user), \
             patch('app.modules.auth.permissions.current_user', new=mock_user), \
             patch('flask_login.utils._get_user', return_value=mock_user):
            
            yield mock_user

    def _configure_test_app(self, app):
        login_manager = LoginManager()
        login_manager.init_app(app)
        login_manager.user_loader(lambda id: MagicMock(id=int(id)))

        app.add_url_rule('/dummy_list', endpoint='admin.list_users', view_func=lambda: 'listed')
        app.add_url_rule('/dummy_view/<int:user_id>', endpoint='admin.view_user', view_func=lambda user_id: 'viewed')

    def test_view_function_delete_user_self_attempt(self, mock_service_instance, mock_auth):
        from app.modules.admin.routes import delete_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/1/delete', method='POST'):
            with patch('app.modules.admin.routes.DeleteUserForm') as MockForm:
                MockForm.return_value.validate_on_submit.return_value = True
                
                target_user = MagicMock(id=1) 
                mock_service_instance.get_user.return_value = target_user
                
                response = delete_user(1)
                
                assert response.status_code == 302
                mock_service_instance.delete_user.assert_not_called()

    def test_view_function_delete_user_admin_attempt(self, mock_service_instance, mock_auth):
        from app.modules.admin.routes import delete_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)

        with app.test_request_context('/users/2/delete', method='POST'):
            with patch('app.modules.admin.routes.DeleteUserForm') as MockForm:
                MockForm.return_value.validate_on_submit.return_value = True
                
                target_user = MagicMock(id=2)
                target_user.has_role.return_value = True
                mock_service_instance.get_user.return_value = target_user

                response = delete_user(2)
                
                assert response.status_code == 302
                mock_service_instance.delete_user.assert_not_called()

    def test_view_function_create_user_post(self, mock_service_instance):
        from app.modules.admin.routes import create_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/create', method='POST'):
             with patch('app.modules.admin.routes.CreateUserForm') as MockForm:
                form = MockForm.return_value
                form.validate_on_submit.return_value = True
                
                mock_service_instance.create_user.return_value = (True, "Ok")
                mock_service_instance.get_all_roles.return_value = []

                response = create_user()
                
                assert response.status_code == 302 
                mock_service_instance.create_user.assert_called_once()

    def test_create_user_form_validation_fails(self, mock_service_instance):
        from app.modules.admin.routes import create_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/create', method='POST'):
            with patch('app.modules.admin.routes.CreateUserForm') as MockForm, \
                 patch('app.modules.admin.routes.render_template') as mock_render:
                
                MockForm.return_value.validate_on_submit.return_value = False
                
                create_user()
                
                mock_service_instance.create_user.assert_not_called()
                mock_render.assert_called()

    def test_edit_user_get_prefills_form(self, mock_service_instance, mock_auth):
        from app.modules.admin.routes import edit_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/1/edit', method='GET'):
             with patch('app.modules.admin.routes.EditUserForm') as MockForm, \
                  patch('app.modules.admin.routes.render_template') as mock_render:
                
                form = MockForm.return_value
                form.validate_on_submit.return_value = False
                
                target_user = MagicMock()
                target_user.id = 1 
                target_user.has_role.return_value = False 
                target_user.email = "existing@email.com"
                target_user.profile.name = "Juan"
                
                role1 = MagicMock()
                role1.id = 10
                role2 = MagicMock()
                role2.id = 20
                target_user.roles = [role1, role2]
                
                mock_service_instance.get_user.return_value = target_user
                
                edit_user(1)
                
                assert form.email.data == "existing@email.com"
                assert form.name.data == "Juan"
                assert form.roles.data == [10, 20]

    def test_list_users_renders_template(self, mock_service_instance):
        from app.modules.admin.routes import list_users
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users', method='GET'):
            with patch('app.modules.admin.routes.render_template') as mock_render, \
                 patch('app.modules.admin.routes.DeleteUserForm') as MockDeleteForm:
                
                user1 = MagicMock(email="normal@user.com", id=1)
                user2 = MagicMock(email="locust@local", id=2)
                mock_service_instance.list_users.return_value = [user1, user2]
                
                list_users()
                
                mock_service_instance.list_users.assert_called_once()
                mock_render.assert_called_once()
                args, kwargs = mock_render.call_args
                assert "listarUsuarios.html" == args[0]
                assert len(kwargs['users']) == 1 

    def test_edit_user_post_success(self, mock_service_instance, mock_auth):
        from app.modules.admin.routes import edit_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/1/edit', method='POST'):
            with patch('app.modules.admin.routes.EditUserForm') as MockForm:
                # Usamos 'form' aquí para evitar NameError si se usaba form_instance
                form = MockForm.return_value
                form.validate_on_submit.return_value = True
                
                target_user = MagicMock(id=1)
                target_user.has_role.return_value = False
                mock_service_instance.get_user.return_value = target_user
                
                mock_service_instance.update_user.return_value = True
                
                response = edit_user(1)
                
                assert response.status_code == 302
                # Aseguramos que se llame con el formulario mockeado
                mock_service_instance.update_user.assert_called_once_with(1, form)

    def test_delete_user_route_success(self, mock_service_instance, mock_auth):
        from app.modules.admin.routes import delete_user
        
        app = Flask(__name__)
        app.config['SECRET_KEY'] = 'key'
        self._configure_test_app(app)
        
        with app.test_request_context('/users/3/delete', method='POST'):
            with patch('app.modules.admin.routes.DeleteUserForm') as MockForm, \
                 patch('app.modules.admin.routes.User') as MockUserRoute:
                
                MockForm.return_value.validate_on_submit.return_value = True
                
                admin_mock = MagicMock()
                admin_mock.id = 1
                MockUserRoute.query.get.return_value = admin_mock
                
                target_user = MagicMock(id=3)
                target_user.has_role.return_value = False
                mock_service_instance.get_user.return_value = target_user
                
                mock_service_instance.delete_user.return_value = True
                
                response = delete_user(3)
                
                assert response.status_code == 302
                mock_service_instance.delete_user.assert_called_once_with(3)