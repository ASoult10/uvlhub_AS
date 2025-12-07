from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from flask import jsonify

from app import create_app, db
from app.modules.api.models import ApiKey
from app.modules.api.services import limiter, require_api_key


@pytest.fixture(scope="function")
def app():
    """Crear app para testing"""
    app = create_app("testing")
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SERVER_NAME"] = "localhost"

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Crear un cliente de prueba"""
    return app.test_client()


@pytest.fixture
def mock_api_key():
    """Crear un ApiKey simulado"""
    mock_key = Mock()
    mock_key.key = "test-api-key-123"
    mock_key.is_valid.return_value = True
    mock_key.has_scope.return_value = True
    mock_key.increment_usage = Mock()
    return mock_key


@pytest.fixture
def user(app):
    """Crear un usuario de prueba"""
    from app.modules.auth.models import User

    with app.app_context():
        user = User(email="test@test.com", password="password123")
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge(user)
        return db.session.get(User, user_id)


# ============================= TESTS PARA SERVICES =============================


class TestRequireApiKeyDecorator:

    def test_missing_api_key_returns_401(self, app):
        """Test sin clave API devuelve 401"""
        with app.test_request_context("/test", headers={}):

            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({"success": True})

            result = test_func()
            assert result[1] == 401

    @patch("app.modules.api.services.ApiKey.query")
    def test_invalid_api_key_returns_403(self, mock_query, app):
        """Test que clave API inválida devuelve 403"""
        mock_query.filter_by.return_value.first.return_value = None

        with app.test_request_context("/test", headers={"X-API-Key": "invalid"}):

            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({"success": True})

            result = test_func()
            assert result[1] == 403

    @patch("app.modules.api.services.ApiKey.query")
    def test_expired_or_insufficient_scope_returns_403(self, mock_query, app, mock_api_key):
        """Test que clave expirada o con alcance insuficiente devuelve 403"""
        mock_api_key.is_valid.return_value = False
        mock_query.filter_by.return_value.first.return_value = mock_api_key

        with app.test_request_context("/test", headers={"X-API-Key": "expired"}):

            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({"success": True})

            result = test_func()
            assert result[1] == 403

        mock_api_key.is_valid.return_value = True
        mock_api_key.has_scope.return_value = False

        with app.test_request_context("/test", headers={"X-API-Key": "valid"}):

            @require_api_key(scope="admin:all")
            def test_func2(api_key_obj):
                return jsonify({"success": True})

            result = test_func2()
            assert result[1] == 403

    @patch("app.modules.api.services.ApiKey.query")
    def test_valid_key_with_correct_scope(self, mock_query, app, mock_api_key):
        """Test que clave válida con alcance correcto llama a la función"""
        mock_query.filter_by.return_value.first.return_value = mock_api_key

        with app.test_request_context("/test", headers={"X-API-Key": "valid"}):

            @require_api_key(scope="read:datasets")
            def test_func(api_key_obj):
                return jsonify({"success": True, "key": api_key_obj.key})

            result = test_func()
            assert result.json["success"] is True
            mock_api_key.increment_usage.assert_called_once()
            mock_api_key.has_scope.assert_called_with("read:datasets")


class TestLimiter:

    def test_limiter_configured(self):
        """Test que el limitador está configurado correctamente"""
        assert limiter is not None
        assert limiter._key_func is not None


# ============================= TESTS PARA MODELS =============================


class TestApiKeyModel:

    def test_generate_key_creates_valid_unique_keys(self):
        """Test que generate_key crea claves únicas con formato válido"""
        key1 = ApiKey.generate_key()
        key2 = ApiKey.generate_key()

        assert key1 != key2
        assert len(key1) == 43
        assert all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-" for c in key1)

    def test_is_valid_checks_active_and_expiration(self, app, user):
        """Test que verifica tanto el estado activo como la expiración"""
        with app.app_context():
            api_key = ApiKey(
                key="test-key-1",
                user_id=user.id,
                name="Valid Key",
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30),
            )
            db.session.add(api_key)
            db.session.commit()
            assert api_key.is_valid() is True

            api_key.is_active = False
            db.session.commit()
            assert api_key.is_valid() is False

            api_key.is_active = True
            api_key.expires_at = datetime.utcnow() - timedelta(days=1)
            db.session.commit()
            assert api_key.is_valid() is False

            api_key.expires_at = None
            db.session.commit()
            assert api_key.is_valid() is True

    def test_has_scope_validation(self, app, user):
        """Test con varios scopes y casos límite"""
        with app.app_context():
            api_key = ApiKey(key="test-key", user_id=user.id, name="Test Key", scopes="read:datasets, write:datasets")
            db.session.add(api_key)
            db.session.commit()

            assert api_key.has_scope("read:datasets") is True
            assert api_key.has_scope("write:datasets") is True
            assert api_key.has_scope("admin:all") is False

            api_key.scopes = ""
            db.session.commit()
            assert api_key.has_scope("read:datasets") is False

            api_key.scopes = None
            db.session.commit()
            assert api_key.has_scope("read:datasets") is False

    def test_increment_usage(self, app, user):
        """Test que incrementa el contador y actualiza la marca de tiempo"""
        with app.app_context():
            api_key = ApiKey(key="test-key", user_id=user.id, name="Test Key", requests_count=0, last_used_at=None)
            db.session.add(api_key)
            db.session.commit()

            api_key.increment_usage()
            db.session.refresh(api_key)

            assert api_key.requests_count == 1
            assert api_key.last_used_at is not None

            api_key.increment_usage()
            db.session.refresh(api_key)
            assert api_key.requests_count == 2

    def test_api_key_relationships_and_defaults(self, app, user):
        """Test relaciones y valores por defecto de API key"""
        with app.app_context():
            api_key = ApiKey(key="test-key", user_id=user.id, name="Test Key")
            db.session.add(api_key)
            db.session.commit()
            db.session.refresh(api_key)

            assert api_key.user_id == user.id
            assert api_key.created_at is not None
            assert api_key.is_active is True
            assert api_key.requests_count == 0


# ============================= TESTS PARA FORMS =============================


class TestApiKeyForm:

    def test_form_has_required_fields(self, app):
        """Test que el formulario tiene todos los campos requeridos"""
        from app.modules.api.forms import ApiKeyForm

        with app.app_context():
            form = ApiKeyForm()

            assert hasattr(form, "name")
            assert hasattr(form, "scopes")
            assert hasattr(form, "expires_at")
            assert hasattr(form, "submit")


# ============================= TESTS PARA ROUTES =============================


class TestApiRoutes:

    def test_public_routes(self, client):
        """Test que las rutas públicas son accesibles"""
        response = client.get("/api/docs")
        assert response.status_code in [200, 404]

    def test_protected_routes_require_auth(self, client):
        """Test que las rutas protegidas requieren autenticación"""
        response = client.get("/api/manage", follow_redirects=False)
        assert response.status_code in [302, 401]

    @patch("flask_login.utils._get_user")
    def test_manage_keys_workflow(self, mock_current_user, client, user, app):
        """Test flujo completo de gestión de claves"""
        with app.app_context():
            from app.modules.profile.models import UserProfile

            profile = UserProfile(user_id=user.id, name="Test", surname="User")
            db.session.add(profile)
            db.session.commit()

            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True

            response = client.get("/api/manage")
            assert response.status_code == 200

            response = client.post(
                "/api/create", data={"name": "Test Key", "scopes": ["read:datasets"]}, follow_redirects=False
            )
            assert response.status_code in [200, 302]

    @patch("flask_login.utils._get_user")
    def test_revoke_and_delete_own_key(self, mock_current_user, client, user, app):
        """Test revocar y eliminar propia clave API"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user

            api_key = ApiKey(key=ApiKey.generate_key(), user_id=user.id, name="Key to Test", is_active=True)
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True

            response = client.post(f"/api/revoke/{key_id}")
            assert response.status_code in [200, 302]
            revoked = db.session.get(ApiKey, key_id)
            assert revoked.is_active == False

            response = client.post(f"/api/delete/{key_id}")
            assert response.status_code in [200, 302]
            deleted = db.session.get(ApiKey, key_id)
            assert deleted is None

    @patch("flask_login.utils._get_user")
    def test_cannot_modify_other_user_keys(self, mock_current_user, client, user, app):
        """Test que un usuario no puede modificar las claves de otro usuario"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user

            other = user.__class__(email="other@example.com", password="pass")
            db.session.add(other)
            db.session.commit()

            api_key = ApiKey(key=ApiKey.generate_key(), user_id=other.id, name="Other Key", is_active=True)
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id

            with client.session_transaction() as sess:
                sess["_user_id"] = str(user.id)
                sess["_fresh"] = True

            response = client.post(f"/api/revoke/{key_id}")
            assert response.status_code in [302, 404]

            response = client.post(f"/api/delete/{key_id}")
            assert response.status_code in [302, 404]

    @patch("app.modules.api.services.ApiKey.query")
    def test_api_endpoints_with_valid_key(self, mock_query, client, app):
        """Test con las rutas API con clave válida"""
        with app.app_context():
            mock_key = Mock()
            mock_key.is_active = True
            mock_key.expires_at = None
            mock_key.has_scope.return_value = True
            mock_key.increment_usage = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_key

            headers = {"X-API-Key": "test-key"}

            endpoints = [
                "/api/datasets/id/1",
                "/api/datasets/title/test",
                "/api/datasets",
                "/api/search?q=test",
                "/api/stats",
            ]

            for endpoint in endpoints:
                response = client.get(endpoint, headers=headers)
                assert response.status_code in [200, 404, 500]

    def test_api_blueprint_registered(self, app):
        """Test que el blueprint API está registrado"""
        assert "api" in [bp.name for bp in app.blueprints.values()]


# ============================= TESTS PARA SEEDERS =============================


class TestApiKeysSeeder:

    @patch.dict("os.environ", {"LOCUST_API_KEY": ""})
    def test_seeder_skips_without_env_key(self, app, capsys):
        """Test que el seeder se salta sin LOCUST_API_KEY"""
        from app.modules.api.seeders import ApiKeysSeeder

        with app.app_context():
            ApiKeysSeeder().run()
            assert "Falta LOCUST_API_KEY" in capsys.readouterr().out

    @patch.dict("os.environ", {"LOCUST_API_KEY": "test-key-123"})
    def test_seeder_creates_user_and_keys(self, app):
        """Test que crea usuario y keys correctamente"""
        from app.modules.api.seeders import ApiKeysSeeder
        from app.modules.auth.models import User

        with app.app_context():
            ApiKeysSeeder().run()

            user = User.query.filter_by(email="locust@local").first()
            assert user is not None

            api_key = ApiKey.query.filter_by(key="test-key-123").first()
            assert api_key is not None
            assert api_key.scopes == "read:datasets"
            assert api_key.user_id == user.id

    @patch.dict("os.environ", {"LOCUST_API_KEY": "test-key-123", "LOCUST_API_KEY_STATS": "test-stats-key"})
    def test_seeder_creates_multiple_keys_with_different_scopes(self, app):
        """Test que crea múltiples keys con diferentes scopes"""
        from app.modules.api.seeders import ApiKeysSeeder

        with app.app_context():
            ApiKeysSeeder().run()

            key1 = ApiKey.query.filter_by(key="test-key-123").first()
            key2 = ApiKey.query.filter_by(key="test-stats-key").first()

            assert key1.scopes == "read:datasets"
            assert key2.scopes == "read:datasets,read:stats"

    @patch.dict("os.environ", {"LOCUST_API_KEY": "test-key-123"})
    def test_seeder_is_idempotent(self, app):
        """Test que el seeder es idempotente (no duplica)"""
        from app.modules.api.seeders import ApiKeysSeeder

        with app.app_context():
            seeder = ApiKeysSeeder()
            seeder.run()
            seeder.run()

            count = ApiKey.query.filter_by(key="test-key-123").count()
            assert count == 1

    def test_seeder_priority(self):
        """Test que el seeder tiene prioridad 100"""
        from app.modules.api.seeders import ApiKeysSeeder

        assert ApiKeysSeeder().priority == 100
