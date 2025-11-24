from flask import render_template, request, jsonify
from flask_login import login_required, current_user
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token, get_jwt
from app.modules.token import token_bp
from app.modules.token.services import TokenService
from app import db

def jsonify_token(token):
    return {
        "id": token.id,
        "code": token.code,
        "is_active": token.is_active,
        "type": token.type.value,
        "expires_at": token.expires_at.isoformat(),
        "created_at": token.created_at.isoformat(),
        "device_info": token.device_info,
        "location_info": token.location_info
    }

@token_bp.route('/token/sessions', methods=['GET'])
@login_required
def sessions_page():
    tokens = TokenService.get_active_tokens_by_user(current_user.id)
    return render_template('token/sessions.html', tokens=tokens)

@token_bp.route('/token/get/id/<int:token_id>', methods=['GET'])
@login_required
def get_token_by_id(self, token_id):
    token = TokenService.get_token_by_id(token_id)
    return jsonify_token(token), 200

@token_bp.route('/token/get/all', methods=['GET'])
@login_required
def get_all_tokens_by_user():
    tokens = TokenService.get_all_tokens_by_user(current_user.id)
    return jsonify([jsonify_token(token) for token in tokens]), 200

@token_bp.route('/token/revoke/<int:token_id>', methods=['DELETE'])
@login_required
def revoke_token(token_id):
    TokenService.revoke_token(token_id, current_user.id)
    return jsonify({"status": "ok", "revoked": token_id}), 200

@token_bp.route('/token/revoke/all', methods=['POST'])
@login_required
def revoke_all_tokens_for_user():
    TokenService.revoke_all_tokens_for_user(current_user.id)
    return jsonify({"status": "ok", "revoked_all": True}), 200

@token_bp.route('/token/create', methods=['POST'])
@login_required
def create_token():
    data = request.json
    data['user_id'] = current_user.id
    new_token = TokenService.save_token(**data)
    return jsonify_token(new_token), 201

@token_bp.route('/token/edit/<int:token_id>', methods=['PUT'])
@login_required
def edit_token(token_id):
    data = request.json
    updated_token = TokenService.edit_token(token_id, **data)
    return jsonify_token(updated_token), 200

@token_bp.route('/token/delete/<int:token_id>', methods=['DELETE'])
@login_required
def delete_token(token_id):
    TokenService.delete_token(token_id)
    return jsonify({"status": "ok", "deleted": token_id}), 200