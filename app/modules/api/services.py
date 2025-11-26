from functools import wraps
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.modules.api.models import ApiKey

# Configuración del rate limiter
limiter = Limiter(
    key_func=lambda: request.headers.get('X-API-Key', get_remote_address()),
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"  # Usa Redis en producción: "redis://localhost:6379"
)

# Wrapper para proteger endpoints con API key

def require_api_key(scope='read:datasets'):
    """
    Decorador para proteger endpoints con API key
    Uso: @require_api_key(scope='read:datasets')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Obtener la API key del header
            api_key = request.headers.get('X-API-Key')
            
            if not api_key:
                return jsonify({
                    'error': 'API key required',
                    'message': 'Please provide an API key in the X-API-Key header'
                }), 401
            
            # 2. Buscar la key en la base de datos
            key_obj = ApiKey.query.filter_by(key=api_key).first()
            
            if not key_obj:
                return jsonify({
                    'error': 'Invalid API key',
                    'message': 'The provided API key does not exist'
                }), 403
            
            # 3. Validar que esté activa y no expirada
            if not key_obj.is_valid():
                return jsonify({
                    'error': 'API key expired or inactive',
                    'message': 'Your API key is no longer valid'
                }), 403
            
            # 4. Validar permisos (scopes)
            if not key_obj.has_scope(scope):
                return jsonify({
                    'error': 'Insufficient permissions',
                    'message': f'This endpoint requires {scope} scope'
                }), 403
            
            # 5. Registrar el uso
            key_obj.increment_usage()
            
            # 6. Ejecutar la función protegida
            return f(api_key_obj=key_obj, *args, **kwargs)
        
        return decorated_function
    return decorator