from functools import wraps
from typing import Iterable
from flask import request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app.modules.api.models import ApiKey

def _rate_limit_key():
    # Prioriza la API Key para rate limit; si no hay, usa IP
    return request.headers.get('X-API-Key') or request.args.get('api_key') or get_remote_address()

# Configuración del rate limiter
limiter = Limiter(
    key_func=_rate_limit_key,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

def _extract_api_key() -> str | None:
    # 1) Header X-API-Key
    key = request.headers.get('X-API-Key')
    if key:
        return key
    # 2) Query param ?api_key=...
    key = request.args.get('api_key')
    if key:
        return key
    # 3) Authorization: ApiKey <key>
    auth = request.headers.get('Authorization', '')
    if auth.startswith('ApiKey '):
        return auth.split(' ', 1)[1].strip() or None
    return None

def _has_required_scopes(allowed: set[str], required: set[str], require_all: bool) -> bool:
    if not required:
        return True
    return required.issubset(allowed) if require_all else bool(allowed.intersection(required))

def require_api_key(scopes: str | Iterable[str] | None = None, require_all: bool = False):
    """
    Protege endpoints con API Key.
    - Fuentes soportadas: header X-API-Key, query param ?api_key=, Authorization: ApiKey <key>
    - scopes: str o iterable (p.ej. ['read:stats','read:status']). None para no exigir scope.
    - require_all: True para exigir todos los scopes, False para cualquiera.
    Inyecta api_key_obj=ApiKey en la vista.
    """
    # Normaliza scopes requeridos
    if scopes is None:
        required_scopes: set[str] = set()
    elif isinstance(scopes, str):
        required_scopes = {scopes}
    else:
        required_scopes = {s for s in scopes if s}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            provided = _extract_api_key()
            if not provided:
                return jsonify({
                    "error": "missing_api_key",
                    "message": "Provide API key in X-API-Key header, ?api_key=, or Authorization: ApiKey <key>"
                }), 401

            key_obj = ApiKey.query.filter_by(key=provided).first()
            if not key_obj:
                return jsonify({
                    "error": "invalid_api_key",
                    "message": "The provided API key does not exist"
                }), 401

            if not key_obj.is_valid():
                return jsonify({
                    "error": "inactive_or_expired",
                    "message": "API key is inactive or expired"
                }), 403

            allowed = {s.strip() for s in (key_obj.scopes or "").split(",") if s.strip()}
            if not _has_required_scopes(allowed, required_scopes, require_all):
                return jsonify({
                    "error": "insufficient_scope",
                    "message": "Required scope(s) not granted",
                    "required": sorted(required_scopes),
                    "granted": sorted(allowed)
                }), 403

            try:
                key_obj.increment_usage()
            except Exception:
                # Evitar fallar el endpoint por métricas de uso
                pass

            return f(api_key_obj=key_obj, *args, **kwargs)
        return decorated_function
    return decorator