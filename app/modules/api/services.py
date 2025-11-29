from functools import wraps
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.modules.api.models import ApiKey

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def require_api_key(scope='read:datasets'):
    """
    Decorador para proteger endpoints con API key
    Uso: @require_api_key(scope='read:datasets')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({
                    'error': 'API key required',
                    'message': 'Please provide an API key in the X-API-Key header'
                }), 401
            
            key_obj = ApiKey.query.filter_by(key=api_key).first()
            
            if not key_obj:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key does not exist'
                }), 403
            
            if not key_obj.is_valid():
                return jsonify({
                    'error': 'API key expired or inactive',
                    'message': 'Your API key is no longer valid'
                }), 403
            
            if not key_obj.has_scope(scope):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires the {scope} scope'
                }), 403
            
            key_obj.increment_usage()
            
            return f(api_key_obj=key_obj, *args, **kwargs)
        
        return decorated_function
    return decorator