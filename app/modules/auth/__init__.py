from core.blueprints.base_blueprint import BaseBlueprint
from .permissions import require_permission

auth_bp = BaseBlueprint("auth", __name__, template_folder="templates")

__all__ = ["require_permission"]
