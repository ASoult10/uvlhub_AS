from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user, login_user, logout_user, login_required
from app.modules.auth import require_permission
from app.modules.admin.services import AdminService
from app.modules.auth.models import User, Role
from app.modules.admin import admin_bp


admin_service = AdminService()

@admin_bp.route("/users")
@login_required
@require_permission("manage_users")
def list_users():
    users = admin_service.list_users()
    return render_template("listarUsuarios.html", users=users)