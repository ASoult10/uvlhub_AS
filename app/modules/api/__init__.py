from flask import Blueprint

# Crea el blueprint para la API
#Los blueprints son mini-aplicaciones modulares en Flask
#Agrupa todas las rutas bajo el prefijo /api
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Importa las rutas después de crear el blueprint
from app.modules.api import routes