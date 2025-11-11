from flask import render_template
from app.modules.token import token_bp


@token_bp.route('/token', methods=['GET'])
def index():
    return render_template('token/index.html')
