from flask_restful import Api
from app.modules.dataset.api import init_blueprint_api
from core.blueprints.base_blueprint import BaseBlueprint

dataset_bp = BaseBlueprint("dataset", __name__, template_folder="templates")

api = Api(dataset_bp)
init_blueprint_api(api)

from app.modules.dataset.import_api import import_api
dataset_bp.register_blueprint(import_api)

from app.modules.dataset import comments_routes  # noqa
