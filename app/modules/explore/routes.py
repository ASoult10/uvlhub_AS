from flask import jsonify, render_template, request, url_for

from app.modules.dataset.models import Author, DSMetaData
from app.modules.dataset.services import DataSetService
from app.modules.explore import explore_bp
from app.modules.explore.forms import ExploreForm
from app.modules.explore.services import ExploreService
from app.modules.profile.models import UserProfile


@explore_bp.route("/explore", methods=["GET", "POST"])
def index():
    if request.method == "GET":
        query = request.args.get("query", "")
        authors = Author.query.with_entities(Author.name).distinct().order_by(Author.name.asc()).all()
        tag_strings = DSMetaData.query.with_entities(DSMetaData.tags).filter(DSMetaData.tags.isnot(None)).all()
        tags = set()
        for (tag_string,) in tag_strings:
            if tag_string:
                tags.update(tag.strip() for tag in tag_string.split(","))
        tags = sorted(list(tags))
        form = ExploreForm()
        return render_template("explore/index.html", form=form, query=query, authors=authors, tags=tags)

    if request.method == "POST":
        criteria = request.get_json()
        datasets = ExploreService().filter(**criteria)

        dataset_service = DataSetService()
        result = []
        for dataset in datasets:
            dataset_dict = dataset.to_dict()

            # Add recommendations for each dataset
            recommendations = dataset_service.get_recommendations(dataset.id, limit=3)
            dataset_dict["recommendations"] = [
                {
                    "title": rec["dataset"].ds_meta_data.title,
                    "url": f"/doi/{rec['dataset'].ds_meta_data.dataset_doi}/",
                    "score": rec["score"],
                    "downloads": rec["downloads"],
                    "coincidences": rec["coincidences"],
                }
                for rec in recommendations
            ]

            # Add creator info for each dataset
            dataset_creator = UserProfile.query.filter_by(user_id=dataset.user_id).first()
            dataset_dict["creator"] = {
                "name": dataset_creator.name,
                "surname": dataset_creator.surname,
                "profile_url": url_for('profile.author_profile', user_id=dataset.user_id)
            } if dataset_creator else None

            result.append(dataset_dict)

        return jsonify(result)
