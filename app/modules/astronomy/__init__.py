from flask import Blueprint

astronomy_bp = Blueprint(
    "astronomy",
    __name__,
    template_folder="templates",
    static_folder="assets",
)

from . import routes  # noqa
