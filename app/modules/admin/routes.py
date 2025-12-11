from flask import current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.modules.admin import admin_bp
from app.modules.admin.forms import DeleteUserForm
from app.modules.admin.services import AdminService
from app.modules.auth import require_permission
from app.modules.auth.models import User
from app.modules.dataset.models import DataSet

admin_service = AdminService()


@admin_bp.route("/users")
@login_required
@require_permission("manage_users")
def list_users():
    users = admin_service.list_users()
    users_forms = {}
    for user in users:
        users_forms[user.id] = DeleteUserForm()
    return render_template("listarUsuarios.html", users=users, users_forms=users_forms)


@admin_bp.route("/users/<int:user_id>")
@login_required
@require_permission("manage_users")
def view_user(user_id):
    page = request.args.get("page", 1, type=int)
    per_page = 5

    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == current_user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )
    total_datasets_count = db.session.query(DataSet).filter(DataSet.user_id == current_user.id).count()
    user = admin_service.get_user(user_id)
    if not user:
        flash("User not found.", "error")
        return redirect(url_for("admin.list_users"))
    return render_template(
        "verUsuario.html", user=user, total_datasets=total_datasets_count, datasets=user_datasets_pagination.items
    )


@admin_bp.route("/users/<int:user_id>/delete", methods=["POST"])
@require_permission("manage_users")
def delete_user(user_id):
    form = DeleteUserForm()
    if not form.validate_on_submit():
        flash("Invalid form submission.", "error")
        return redirect(url_for("admin.list_users"))

    admin_user_id = current_user.id
    if admin_user_id == user_id:
        flash("You cannot delete your own account.", "warning")
        return redirect(url_for("admin.list_users"))

    admin_user = User.query.get(admin_user_id)
    current_app.logger.info(f"Attempting to delete user with id={user_id} by admin id={admin_user.id}")

    try:
        success = admin_service.delete_user(user_id)
    except Exception as e:
        current_app.logger.error(f"Error deleting user with id={user_id}: {e}")
        flash("An error occurred while trying to delete the user.", "error")
        return redirect(url_for("admin.list_users"))

    if success:
        flash("User deleted successfully.", "success")
    else:
        flash("User not found.", "error")

    return redirect(url_for("admin.list_users"))
