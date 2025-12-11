import logging

from flask import render_template

from app.modules.dataset.services import DataSetService
from app.modules.profile.models import UserProfile
from app.modules.public import public_bp

logger = logging.getLogger(__name__)


@public_bp.route("/")
def index():
    logger.info("Access index")
    dataset_service = DataSetService()

    # Statistics: total datasets and feature models
    datasets_counter = dataset_service.count_synchronized_datasets()

    # Statistics: total downloads
    total_dataset_downloads = dataset_service.total_dataset_downloads()

    # Statistics: total views
    total_dataset_views = dataset_service.total_dataset_views()

    # Get latest datasets
    latest_datasets = dataset_service.latest_synchronized()
    logger.info(f"Found {len(latest_datasets)} latest datasets")

    # Get recommendations for each dataset
    recommendations_map = {}
    try:
        for dataset in latest_datasets:
            logger.info(
                f"Getting recommendations for dataset {
                    dataset.id}: "
                f"{
                    dataset.ds_meta_data.title}"
            )
            recommendations = dataset_service.get_recommendations(dataset.id, limit=3)
            logger.info(
                f"Found {
                    len(recommendations)} recommendations for dataset {
                    dataset.id}"
            )
            recommendations_map[dataset.id] = recommendations
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}", exc_info=True)

    logger.info(
        f"Total datasets: {
            len(latest_datasets)}, "
        f"recommendations_map size: {
            len(recommendations_map)}"
    )

    for dataset in latest_datasets:
        try:
            dataset.creator = UserProfile.query.filter_by(user_id=dataset.user_id).first()
        except Exception as e:
            logger.error(f"Error getting creator for dataset {dataset.id}: {e}", exc_info=True)

    return render_template(
        "public/index.html",
        datasets=latest_datasets,
        recommendations_map=recommendations_map,
        datasets_counter=datasets_counter,
        total_dataset_downloads=total_dataset_downloads,
        total_dataset_views=total_dataset_views,
    )
