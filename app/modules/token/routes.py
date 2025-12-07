from flask import jsonify, render_template, request
from flask_jwt_extended import get_jwt
from flask_login import current_user, login_required

from app.modules.token import token_bp
from app.modules.token.services import TokenService

token_service = TokenService()


@token_bp.route("/token/sessions", methods=["GET"])
@login_required
def sessions_page():
    tokens = token_service.get_active_tokens_by_user(current_user.id)
    current_token = get_jwt()
    for token in tokens:
        token.is_current = token.jti == current_token["jti"]

    return render_template("token/sessions.html", tokens=tokens)


@token_bp.route("/token/revoke/<int:token_id>", methods=["PUT"])
@login_required
def revoke_token(token_id):
    token_service.revoke_token(token_id, current_user.id)
    return jsonify({"status": "ok", "revoked": token_id}), 200


@token_bp.route("/token/revoke/all", methods=["PUT"])
@login_required
def revoke_all_tokens_for_user():
    token_service.revoke_all_tokens_for_user(current_user.id)
    return jsonify({"status": "ok", "revoked_all": True}), 200
