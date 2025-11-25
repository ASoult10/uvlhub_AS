import logging
from flask import request, jsonify
from flask_login import login_required, current_user

from app.modules.dataset import dataset_bp
from app.modules.dataset.services_comments import DSCommentService

logger = logging.getLogger(__name__)
comment_service = DSCommentService()


# GET /dataset/<dataset_id>/comments/
@dataset_bp.route("/dataset/<int:dataset_id>/comments/", methods=["GET"])
def list_dataset_comments(dataset_id: int):
    try:
        comments = comment_service.list_visible(dataset_id)
        return jsonify([c.to_dict() for c in comments]), 200
    except Exception as exc:
        logger.exception("Error listing comments")
        return jsonify({"error": str(exc)}), 500


# POST /dataset/<dataset_id>/comments/
@dataset_bp.route("/dataset/<int:dataset_id>/comments/", methods=["POST"])
@login_required
def create_dataset_comment(dataset_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        content = payload.get("content") or request.form.get("content") or ""
        comment, err = comment_service.add_comment(dataset_id, current_user.id, content)
        if err:
            return jsonify({"error": err}), 400
        return jsonify(comment.to_dict()), 201
    except Exception as exc:
        logger.exception("Error creating comment")
        return jsonify({"error": str(exc)}), 500


# POST /dataset/<dataset_id>/comments/<comment_id>/moderate
@dataset_bp.route("/dataset/<int:dataset_id>/comments/<int:comment_id>/moderate", methods=["POST"])
@login_required
def moderate_dataset_comment(dataset_id: int, comment_id: int):
    try:
        payload = request.get_json(silent=True) or {}
        action = (payload.get("action") or request.form.get("action") or "").lower().strip()
        ok, err = comment_service.moderate(dataset_id, comment_id, action, current_user)
        if not ok:
            status = 403 if err and "permission" in (err or "").lower() else 400
            return jsonify({"error": err or "Unknown error"}), status
        return jsonify({"success": True}), 200
    except Exception as exc:
        logger.exception("Error moderating comment")
        return jsonify({"error": str(exc)}), 500
