import logging
import sys

from flask import abort, current_app, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app import db
from app.modules.auth.models import User
from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DataSet
from app.modules.profile import profile_bp
from app.modules.profile.forms import UserProfileForm
from app.modules.profile.services import UserProfileService

logger = logging.getLogger(__name__)


@profile_bp.route("/profile/edit", methods=["GET", "POST"])
@login_required
def edit_profile():
    auth_service = AuthenticationService()
    profile = auth_service.get_authenticated_user_profile
    #print(f"Found auth profile {profile}", flush=True)


    if not profile:
        current_app.logger.debug(f"redirect to index")

        return redirect(url_for("public.index"))

    form = UserProfileForm()
    if request.method == "POST":
        service = UserProfileService()
        result, errors = service.update_profile(current_user.id, form)
        print(f"Result {result}", flush=True)
        print(f"Result {errors}", flush=True)


        return service.handle_service_response(
            result, errors, "profile.edit_profile", "Profile updated successfully", "profile/edit.html", form
        )

    print("Goes past method because", flush=True)
    print(f"{request}", flush=True)


    return render_template("profile/edit.html", form=form)


@profile_bp.route("/profile/summary")
@login_required
def my_profile():
    page = request.args.get("page", 1, type=int)
    per_page = 5


    user_datasets_pagination = (
        db.session.query(DataSet)
        .filter(DataSet.user_id == current_user.id)
        .order_by(DataSet.created_at.desc())
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    total_datasets_count = db.session.query(DataSet).filter(DataSet.user_id == current_user.id).count()
    roles_name = [r.name for r in current_user.roles] if current_user.roles else "NNone"

    print(user_datasets_pagination.items)

    return render_template(
        "profile/summary.html",
        user_profile=current_user.profile,
        user=current_user,
        datasets=user_datasets_pagination.items,
        pagination=user_datasets_pagination,
        total_datasets=total_datasets_count,
        roles_name=roles_name,
    )


@profile_bp.route("/profile/<int:user_id>")
def author_profile(user_id):

    user = User.query.filter(User.id == user_id).first()

    if not user:
        logger.warning(f"Usuario con id {user_id} no encontrado.")
        abort(404)

    datasets = db.session.query(DataSet).filter(DataSet.user_id == user.id).all()
    datasets_counter = len(datasets)

    downloads_counter = 0
    for dataset in datasets:
        downloads_counter += dataset.download_count

    return render_template(
        "profile/author_profile.html",
        user=user,
        profile=user.profile,
        datasets=datasets,
        datasets_counter=datasets_counter,
        downloads_counter=downloads_counter,
    )
