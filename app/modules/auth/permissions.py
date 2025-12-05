from functools import wraps
from flask import abort
from flask_login import current_user

def require_permission(permission_name: str):
    """Decorator to require a specific permission for a view function."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)  # Unauthorized
            if not current_user.has_permission(permission_name):
                abort(403)  # Forbidden

            return f(*args, **kwargs)
        return wrapped
    return decorator