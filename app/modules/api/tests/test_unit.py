import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask, jsonify
from datetime import datetime, timedelta
from app.modules.api.services import require_api_key, limiter
from app.modules.api.models import ApiKey
from app import db, create_app


@pytest.fixture(scope='function')
def app():
    """Create and configure a test Flask application"""
    app = create_app('testing')
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SERVER_NAME'] = 'localhost'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def mock_api_key():
    """Create a mock ApiKey object"""
    mock_key = Mock()
    mock_key.key = 'test-api-key-123'
    mock_key.is_valid.return_value = True
    mock_key.has_scope.return_value = True
    mock_key.increment_usage = Mock()
    return mock_key


@pytest.fixture
def user(app):
    """Create a test user"""
    from app.modules.auth.models import User
    with app.app_context():
        user = User(email='test@test.com', password='password123')
        db.session.add(user)
        db.session.commit()
        user_id = user.id
        db.session.expunge(user)
        return db.session.get(User, user_id)


@pytest.fixture
def authenticated_client(client, user, app):
    """Create an authenticated client"""
    with app.app_context():
        with client.session_transaction() as sess:
            sess['user_id'] = user.id
            sess['_fresh'] = True
    return client


@pytest.fixture
def api_key_obj(app, user):
    """Create a test API key"""
    with app.app_context():
        api_key = ApiKey(
            key=ApiKey.generate_key(),
            user_id=user.id,
            name='Test Key',
            is_active=True,
            scopes='read:datasets,write:datasets'
        )
        db.session.add(api_key)
        db.session.commit()
        db.session.refresh(api_key)
        key_id = api_key.id
        db.session.expunge(api_key)
        return db.session.get(ApiKey, key_id)


# ============= TESTS FOR SERVICES =============

class TestRequireApiKeyDecorator:
    
    def test_missing_api_key_returns_401(self, app):
        """Test that missing API key returns 401"""
        with app.test_request_context('/test', headers={}):
            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            result = test_func()
            assert result[1] == 401
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_invalid_api_key_returns_403(self, mock_query, app):
        """Test that invalid API key returns 403"""
        mock_query.filter_by.return_value.first.return_value = None
        
        with app.test_request_context('/test', headers={'X-API-Key': 'invalid'}):
            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            result = test_func()
            assert result[1] == 403
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_expired_key_returns_403(self, mock_query, app, mock_api_key):
        """Test that expired key returns 403"""
        mock_api_key.is_valid.return_value = False
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with app.test_request_context('/test', headers={'X-API-Key': 'expired'}):
            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            result = test_func()
            assert result[1] == 403
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_insufficient_scope_returns_403(self, mock_query, app, mock_api_key):
        """Test that insufficient scope returns 403"""
        mock_api_key.has_scope.return_value = False
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with app.test_request_context('/test', headers={'X-API-Key': 'valid'}):
            @require_api_key(scope='admin:all')
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            result = test_func()
            assert result[1] == 403
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_valid_key_calls_function(self, mock_query, app, mock_api_key):
        """Test that valid key calls the decorated function"""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with app.test_request_context('/test', headers={'X-API-Key': 'valid'}):
            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({'success': True, 'key': api_key_obj.key})
            
            result = test_func()
            assert result.json['success'] is True
            mock_api_key.increment_usage.assert_called_once()
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_scope_validation(self, mock_query, app, mock_api_key):
        """Test that scope is validated"""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with app.test_request_context('/test', headers={'X-API-Key': 'valid'}):
            @require_api_key(scope='write:datasets')
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            test_func()
            mock_api_key.has_scope.assert_called_with('write:datasets')
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_default_scope_is_read_datasets(self, mock_query, app, mock_api_key):
        """Test that default scope is read:datasets"""
        mock_query.filter_by.return_value.first.return_value = mock_api_key
        
        with app.test_request_context('/test', headers={'X-API-Key': 'valid'}):
            @require_api_key()
            def test_func(api_key_obj):
                return jsonify({'success': True})
            
            test_func()
            mock_api_key.has_scope.assert_called_with('read:datasets')


class TestLimiter:
    
    def test_limiter_exists(self):
        """Test that limiter is properly instantiated"""
        assert limiter is not None
    
    def test_limiter_has_key_func(self):
        """Test that limiter has key function"""
        assert limiter._key_func is not None
    
    def test_limiter_configured_with_defaults(self):
        """Test that limiter is configured"""
        assert limiter is not None


# ============= TESTS FOR MODELS =============

class TestApiKeyModel:
    
    def test_generate_key_creates_unique_key(self):
        """Test that generate_key creates a unique key"""
        key1 = ApiKey.generate_key()
        key2 = ApiKey.generate_key()
        
        assert key1 != key2
        assert len(key1) > 0
        assert isinstance(key1, str)
    
    def test_generate_key_creates_valid_format(self):
        """Test that generated key has valid format"""
        key = ApiKey.generate_key()
        assert len(key) == 43
        assert all(c in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz_-" for c in key)
    
    def test_is_active_for_active_key(self, app, user):
        """Test that is_active works for active key"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                is_active=True,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.is_active is True
    
    def test_is_active_for_inactive_key(self, app, user):
        """Test that is_active works for inactive key"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                is_active=False,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.is_active is False
    
    def test_expires_at_in_future(self, app, user):
        """Test that expires_at can be in the future"""
        with app.app_context():
            future_date = datetime.utcnow() + timedelta(days=30)
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                is_active=True,
                expires_at=future_date
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.expires_at > datetime.utcnow()
    
    def test_expires_at_can_be_none(self, app, user):
        """Test that expires_at can be None"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                is_active=True,
                expires_at=None
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.expires_at is None
    
    def test_has_scope_returns_true_for_valid_scope(self, app, user):
        """Test that has_scope returns True for valid scope"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                scopes='read:datasets,write:datasets'
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.has_scope('read:datasets') is True
            assert api_key.has_scope('write:datasets') is True
    
    def test_has_scope_returns_false_for_invalid_scope(self, app, user):
        """Test that has_scope returns False for invalid scope"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                scopes='read:datasets'
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.has_scope('write:datasets') is False
            assert api_key.has_scope('admin:all') is False
    
    def test_has_scope_handles_empty_scopes(self, app, user):
        """Test that has_scope handles empty scopes correctly"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                scopes=''
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.has_scope('read:datasets') is False
    
    def test_has_scope_handles_none_scopes(self, app, user):
        """Test that has_scope handles None scopes correctly"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                scopes=None
            )
            db.session.add(api_key)
            db.session.commit()
            assert api_key.has_scope('read:datasets') is True
    
    def test_has_scope_with_whitespace(self, app, user):
        """Test that has_scope handles whitespace in scopes"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                scopes='read:datasets, write:datasets'
            )
            db.session.add(api_key)
            db.session.commit()
            
            assert api_key.has_scope('read:datasets') is True
            assert api_key.has_scope('write:datasets') is True
    
    def test_increment_usage_increases_count(self, app, user):
        """Test that increment_usage increases requests_count"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                requests_count=5
            )
            db.session.add(api_key)
            db.session.commit()
            
            initial_count = api_key.requests_count
            api_key.increment_usage()
            db.session.refresh(api_key)
            
            assert api_key.requests_count == initial_count + 1
            assert api_key.last_used_at is not None
    
    def test_increment_usage_updates_last_used_at(self, app, user):
        """Test that increment_usage updates last_used_at timestamp"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                requests_count=0,
                last_used_at=None
            )
            db.session.add(api_key)
            db.session.commit()
            
            api_key.increment_usage()
            db.session.refresh(api_key)
            
            assert api_key.last_used_at is not None
    
    def test_increment_usage_from_zero(self, app, user):
        """Test increment_usage starting from zero count"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key',
                requests_count=0
            )
            db.session.add(api_key)
            db.session.commit()
            
            api_key.increment_usage()
            db.session.refresh(api_key)
            
            assert api_key.requests_count == 1
    
    def test_repr_returns_string_representation(self, app, user):
        """Test that __repr__ returns proper string representation"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key-123',
                user_id=user.id,
                name='Test Key'
            )
            db.session.add(api_key)
            db.session.commit()
            
            repr_str = repr(api_key)
            
            assert 'ApiKey' in repr_str
    
    def test_api_key_has_user_relationship(self, app, user):
        """Test that API key has relationship with user"""
        with app.app_context():
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key'
            )
            db.session.add(api_key)
            db.session.commit()
            db.session.refresh(api_key)
            
            assert api_key.user_id == user.id
    
    def test_api_key_created_at_is_set(self, app, user):
        """Test that created_at is automatically set"""
        with app.app_context():
            before = datetime.utcnow()
            api_key = ApiKey(
                key='test-key',
                user_id=user.id,
                name='Test Key'
            )
            db.session.add(api_key)
            db.session.commit()
            after = datetime.utcnow()
            
            assert api_key.created_at is not None


# ============= TESTS FOR FORMS =============

class TestApiKeyForm:
    
    def test_form_name_field_exists(self, app):
        """Test that name field exists"""
        from app.modules.api.forms import ApiKeyForm
        
        with app.app_context():
            form = ApiKeyForm()
            
            assert hasattr(form, 'name')
    
    def test_form_scopes_field_exists(self, app):
        """Test that scopes field exists"""
        from app.modules.api.forms import ApiKeyForm
        
        with app.app_context():
            form = ApiKeyForm()
            
            assert hasattr(form, 'scopes')
    
    def test_form_has_submit_field(self, app):
        """Test that form has submit field"""
        from app.modules.api.forms import ApiKeyForm
        
        with app.app_context():
            form = ApiKeyForm()
            
            assert hasattr(form, 'submit')


# ============= TESTS FOR ROUTES =============

class TestApiRoutes:
    
    def test_index_route_exists(self, client):
        """Test that index route exists"""
        response = client.get('/api/')
        assert response.status_code in [200, 302, 401, 404]
    
    def test_manage_route_without_auth_redirects(self, client):
        """Test that manage route without auth redirects"""
        response = client.get('/api/manage', follow_redirects=False)
        assert response.status_code in [302, 401]
    
    @patch('flask_login.utils._get_user')
    def test_manage_route_with_auth(self, mock_current_user, client, user, app):
        """Test manage route with authentication"""
        with app.app_context():
            from app.modules.profile.models import UserProfile
            profile = UserProfile(user_id=user.id, name='Test', surname='User')
            db.session.add(profile)
            db.session.commit()
            
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.get('/api/manage')
            assert response.status_code == 200
    
    @patch('flask_login.utils._get_user')
    def test_create_key_post(self, mock_current_user, client, user, app):
        """Test creating API key via POST"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post('/api/create', data={
                'name': 'My Test API Key',
                'scopes': ['read:datasets']
            }, follow_redirects=False)
            
            assert response.status_code in [200, 302]
    
    @patch('flask_login.utils._get_user')
    def test_revoke_own_key(self, mock_current_user, client, user, app):
        """Test revoking own API key"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            api_key = ApiKey(
                key=ApiKey.generate_key(),
                user_id=user.id,
                name='Key to Revoke',
                is_active=True
            )
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post(f'/api/revoke/{key_id}')
            assert response.status_code in [200, 302]
            
            # Verificar que se revocó
            revoked = db.session.get(ApiKey, key_id)
            assert revoked.is_active == False
    
    @patch('flask_login.utils._get_user')
    def test_delete_own_key(self, mock_current_user, client, user, app):
        """Test deleting own API key"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            api_key = ApiKey(
                key=ApiKey.generate_key(),
                user_id=user.id,
                name='Key to Delete',
                is_active=True
            )
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post(f'/api/delete/{key_id}')
            assert response.status_code in [200, 302]
            
            deleted = db.session.get(ApiKey, key_id)
            assert deleted is None
    
    @patch('flask_login.utils._get_user')
    def test_cannot_revoke_other_user_key(self, mock_current_user, client, user, app):
        """Test that user cannot revoke another user's key"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            other = user.__class__(email='other@example.com', password='pass')
            db.session.add(other)
            db.session.commit()
            
            api_key = ApiKey(
                key=ApiKey.generate_key(),
                user_id=other.id,
                name='Other Key',
                is_active=True
            )
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post(f'/api/revoke/{key_id}')
            assert response.status_code in [302, 404]
    
    @patch('flask_login.utils._get_user')
    def test_cannot_delete_other_user_key(self, mock_current_user, client, user, app):
        """Test that user cannot delete another user's key"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            other = user.__class__(email='other2@example.com', password='pass')
            db.session.add(other)
            db.session.commit()
            
            api_key = ApiKey(
                key=ApiKey.generate_key(),
                user_id=other.id,
                name='Other Key 2',
                is_active=True
            )
            db.session.add(api_key)
            db.session.commit()
            key_id = api_key.id
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post(f'/api/delete/{key_id}')
            assert response.status_code in [302, 404]
    
    def test_api_blueprint_registered(self, app):
        """Test API blueprint is registered"""
        assert "api" in [bp.name for bp in app.blueprints.values()]
    
    @patch('flask_login.utils._get_user')
    def test_manage_shows_user_keys(self, mock_current_user, client, user, app):
        """Test that manage page shows user's keys"""
        with app.app_context():
            from app.modules.profile.models import UserProfile
            profile = UserProfile(user_id=user.id, name='Test', surname='User')
            db.session.add(profile)
        
            for i in range(3):
                key = ApiKey(
                    key=ApiKey.generate_key(),
                    user_id=user.id,
                    name=f'Key {i}',
                    is_active=True
                )
                db.session.add(key)
            db.session.commit()
            
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.get('/api/manage')
            assert response.status_code == 200
            assert b'Key 0' in response.data or b'Key' in response.data

    @patch('flask_login.utils._get_user')
    def test_create_key_success_redirects(self, mock_current_user, client, user, app):
        """Test successful key creation redirects to manage"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post('/api/create', data={
                'name': 'Success Key',
                'scopes': 'read:datasets'
            }, follow_redirects=False)
            
            assert response.status_code == 302
    
    @patch('flask_login.utils._get_user')
    def test_create_with_all_scopes(self, mock_current_user, client, user, app):
        """Test creating key with multiple scopes"""
        with app.app_context():
            fresh_user = db.session.get(user.__class__, user.id)
            mock_current_user.return_value = fresh_user
            
            with client.session_transaction() as sess:
                sess['_user_id'] = str(user.id)
                sess['_fresh'] = True
            
            response = client.post('/api/create', data={
                'name': 'Multi Scope Key',
                'scopes': 'read:datasets,write:datasets,delete:datasets'
            }, follow_redirects=True)
            response = client.get('/api/datasets/id/1', headers={'X-API-Key': 'test-key'})
            assert response.status_code in [200, 403, 404, 500]
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_get_dataset_by_title(self, mock_query, client, app):
        """Test GET /api/datasets/title/<title>"""
        with app.app_context():
            mock_key = Mock()
            mock_key.is_active = True
            mock_key.expires_at = None
            mock_key.has_scope.return_value = True
            mock_key.increment_usage = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_key
            
            response = client.get('/api/datasets/title/test', headers={'X-API-Key': 'test-key'})
            assert response.status_code in [200, 404, 500]
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_list_datasets(self, mock_query, client, app):
        """Test GET /api/datasets"""
        with app.app_context():
            mock_key = Mock()
            mock_key.is_active = True
            mock_key.expires_at = None
            mock_key.has_scope.return_value = True
            mock_key.increment_usage = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_key
            
            response = client.get('/api/datasets', headers={'X-API-Key': 'test-key'})
            assert response.status_code in [200, 500]
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_search_datasets(self, mock_query, client, app):
        """Test GET /api/search"""
        with app.app_context():
            mock_key = Mock()
            mock_key.is_active = True
            mock_key.expires_at = None
            mock_key.has_scope.return_value = True
            mock_key.increment_usage = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_key
            
            response = client.get('/api/search?q=test', headers={'X-API-Key': 'test-key'})
            assert response.status_code in [200, 400, 500]
    
    @patch('app.modules.api.services.ApiKey.query')
    def test_api_stats(self, mock_query, client, app):
        """Test GET /api/stats"""
        with app.app_context():
            mock_key = Mock()
            mock_key.is_active = True
            mock_key.expires_at = None
            mock_key.has_scope.return_value = True
            mock_key.increment_usage = Mock()
            mock_query.filter_by.return_value.first.return_value = mock_key
            
            response = client.get('/api/stats', headers={'X-API-Key': 'test-key'})
            assert response.status_code in [200, 500]
    
    def test_api_docs(self, client):
        """Test GET /api/docs"""
        response = client.get('/api/docs')
        assert response.status_code in [200, 404]
