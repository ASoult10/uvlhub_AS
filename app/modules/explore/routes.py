from flask import jsonify, render_template, request

from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService
from app.modules.dataset.models import Author


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        query = request.args.get("query", "")
        authors = Author.query.with_entities(Author.name).distinct().order_by(Author.name.asc()).all()
        form = ExploreForm()
        return render_template("explore/index.html", form=form, query=query, authors=authors)

    if request.method == "POST":
        criteria = request.get_json()
        datasets = ExploreService().filter(**criteria)
        return jsonify([dataset.to_dict() for dataset in datasets])
