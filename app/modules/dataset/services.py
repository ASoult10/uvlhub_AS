import hashlib
import logging
import os
import shutil
import uuid
from typing import Optional

from flask import request

from app.modules.auth.services import AuthenticationService
from app.modules.dataset.models import DataSet, DSMetaData, DSViewRecord, Observation
from app.modules.dataset.repositories import (
    AuthorRepository,
    DataSetRepository,
    DOIMappingRepository,
    DSDownloadRecordRepository,
    DSMetaDataRepository,
    DSViewRecordRepository,
)
from app.modules.featuremodel.repositories import FeatureModelRepository, FMMetaDataRepository
from app.modules.hubfile.repositories import (
    HubfileDownloadRecordRepository,
    HubfileRepository,
    HubfileViewRecordRepository,
)
from core.services.BaseService import BaseService

logger = logging.getLogger(__name__)


def calculate_checksum_and_size(file_path):
    file_size = os.path.getsize(file_path)
    with open(file_path, "rb") as file:
        content = file.read()
        hash_md5 = hashlib.md5(content, usedforsecurity=False).hexdigest()
        return hash_md5, file_size


class DataSetService(BaseService):
    def __init__(self):
        super().__init__(DataSetRepository())
        self.feature_model_repository = FeatureModelRepository()
        self.author_repository = AuthorRepository()
        self.dsmetadata_repository = DSMetaDataRepository()
        self.fmmetadata_repository = FMMetaDataRepository()
        self.dsdownloadrecord_repository = DSDownloadRecordRepository()
        self.hubfiledownloadrecord_repository = HubfileDownloadRecordRepository()
        self.hubfilerepository = HubfileRepository()
        self.dsviewrecord_repostory = DSViewRecordRepository()
        self.hubfileviewrecord_repository = HubfileViewRecordRepository()

    def move_feature_models(self, dataset: DataSet):
        current_user = AuthenticationService().get_authenticated_user()
        source_dir = current_user.temp_folder()

        working_dir = os.getenv("WORKING_DIR", "")
        dest_dir = os.path.join(working_dir, "uploads", f"user_{current_user.id}", f"dataset_{dataset.id}")

        os.makedirs(dest_dir, exist_ok=True)

        for feature_model in dataset.feature_models:
            uvl_filename = feature_model.fm_meta_data.uvl_filename
            shutil.move(os.path.join(source_dir, uvl_filename), dest_dir)

    def get_synchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_synchronized(current_user_id)

    def get_unsynchronized(self, current_user_id: int) -> DataSet:
        return self.repository.get_unsynchronized(current_user_id)

    def get_unsynchronized_dataset(self, current_user_id: int, dataset_id: int) -> DataSet:
        return self.repository.get_unsynchronized_dataset(current_user_id, dataset_id)

    def latest_synchronized(self):
        return self.repository.latest_synchronized()

    def count_synchronized_datasets(self):
        return self.repository.count_synchronized_datasets()

    def count_feature_models(self):
        return self.feature_model_service.count_feature_models()

    def count_authors(self) -> int:
        return self.author_repository.count()

    def count_dsmetadata(self) -> int:
        return self.dsmetadata_repository.count()

    def total_dataset_downloads(self) -> int:
        return self.dsdownloadrecord_repository.total_dataset_downloads()

    def total_dataset_views(self) -> int:
        return self.dsviewrecord_repostory.total_dataset_views()

    def create_from_form(self, form, current_user) -> DataSet:
        main_author = {
            "name": f"{current_user.profile.surname}, {current_user.profile.name}",
            "affiliation": current_user.profile.affiliation,
            "orcid": current_user.profile.orcid,
        }
        try:
            logger.info(f"Creating dsmetadata...: {form.get_dsmetadata()}")
            dsmetadata = self.dsmetadata_repository.create(**form.get_dsmetadata())

            # Autores del dataset (autor principal + adicionales)
            for author_data in [main_author] + form.get_authors():
                author = self.author_repository.create(commit=False, ds_meta_data_id=dsmetadata.id, **author_data)
                dsmetadata.authors.append(author)

            # Crear dataset
            dataset = self.create(commit=False, user_id=current_user.id, ds_meta_data_id=dsmetadata.id)

            # ==========================
            # NUEVO: crear observaciones
            # ==========================
            observations_data = form.get_observations()
            logger.info(f"Creating {len(observations_data)} observations from form...")
            for obs_data in observations_data:
                obs = Observation(
                    ds_meta_data_id=dsmetadata.id,
                    object_name=obs_data["object_name"],
                    ra=obs_data["ra"],
                    dec=obs_data["dec"],
                    magnitude=obs_data["magnitude"],
                    observation_date=obs_data["observation_date"],
                    filter_used=obs_data["filter_used"],
                    notes=obs_data["notes"],
                )
                self.repository.session.add(obs)
            # ==========================

            # Feature models
            for feature_model in form.feature_models:
                uvl_filename = feature_model.uvl_filename.data
                fmmetadata = self.fmmetadata_repository.create(commit=False, **feature_model.get_fmmetadata())
                for author_data in feature_model.get_authors():
                    author = self.author_repository.create(commit=False, fm_meta_data_id=fmmetadata.id, **author_data)
                    fmmetadata.authors.append(author)

                fm = self.feature_model_repository.create(
                    commit=False, data_set_id=dataset.id, fm_meta_data_id=fmmetadata.id
                )

                # associated files in feature model
                file_path = os.path.join(current_user.temp_folder(), uvl_filename)
                checksum, size = calculate_checksum_and_size(file_path)

                file = self.hubfilerepository.create(
                    commit=False, name=uvl_filename, checksum=checksum, size=size, feature_model_id=fm.id
                )
                fm.files.append(file)

            self.repository.session.commit()
        except Exception as exc:
            logger.info(f"Exception creating dataset from form...: {exc}")
            self.repository.session.rollback()
            raise exc
        return dataset

    def update_dsmetadata(self, id, **kwargs):
        return self.dsmetadata_repository.update(id, **kwargs)

    def get_uvlhub_doi(self, dataset: DataSet) -> str:
        domain = os.getenv("DOMAIN", "localhost")
        return f"http://{domain}/doi/{dataset.ds_meta_data.dataset_doi}"

    def get_recommendations(self, dataset_id: int, limit: int = 10):
        """
        Get recommended datasets based on tag, author, downloads, and recency.

        Scoring system:
        - Downloads: 3 pts max (partitioned into 3 tiers)
        - Recency: 3 pts max (partitioned into 3 tiers)
        - Coincidences: 4 pts max (based on matching tags/authors)

        Only datasets with at least one tag or author match are recommended.
        """
        logger.info(f"=== get_recommendations called for dataset_id={dataset_id}, limit={limit} ===")

        # Get the current dataset
        current_dataset = self.repository.get_by_id(dataset_id)
        if not current_dataset:
            logger.warning(f"Dataset {dataset_id} not found")
            return []

        logger.info(f"Current dataset: {current_dataset.ds_meta_data.title}")

        # Get current dataset's tags and authors
        current_tags = set()
        if current_dataset.ds_meta_data.tags:
            current_tags = {tag.strip().lower() for tag in current_dataset.ds_meta_data.tags.split(",")}

        current_authors = {author.name.strip().lower() for author in current_dataset.ds_meta_data.authors}

        logger.info(f"Current tags: {current_tags}")
        logger.info(f"Current authors: {current_authors}")

        # Get all other datasets
        all_datasets = DataSet.query.filter(DataSet.id != dataset_id).all()

        logger.info(f"Found {len(all_datasets)} other datasets to compare")

        if not all_datasets:
            logger.warning("No other datasets found")
            return []

        # First pass: Filter datasets with at least one tag or author match
        candidates = []
        for dataset in all_datasets:
            dataset_tags = set()
            if dataset.ds_meta_data.tags:
                dataset_tags = {tag.strip().lower() for tag in dataset.ds_meta_data.tags.split(",")}

            dataset_authors = {author.name.strip().lower() for author in dataset.ds_meta_data.authors}

            # Check for any coincidence
            tag_matches = current_tags & dataset_tags
            author_matches = current_authors & dataset_authors

            if tag_matches or author_matches:
                # Count total coincidences
                total_coincidences = len(tag_matches) + len(author_matches)

                # Get download count
                download_count = self.dsdownloadrecord_repository.count_downloads_for_dataset(dataset.id)

                logger.info(
                    f"  Candidate: {dataset.ds_meta_data.title} - "
                    f"tags:{tag_matches}, authors:{author_matches}, downloads:{download_count}"
                )

                candidates.append(
                    {
                        "dataset": dataset,
                        "coincidences": total_coincidences,
                        "downloads": download_count,
                        "created_at": dataset.created_at,
                    }
                )

        logger.info(f"Found {len(candidates)} candidates with matching tags/authors")

        if not candidates:
            logger.warning("No candidates with matching tags/authors")
            return []

        # Extract downloads and dates for partitioning
        downloads_list = sorted([c["downloads"] for c in candidates])
        dates_list = sorted([c["created_at"] for c in candidates])

        # Create 3-tier partitions for downloads
        n_downloads = len(downloads_list)
        if n_downloads >= 3:
            download_tier1_max = downloads_list[n_downloads // 3]
            download_tier2_max = downloads_list[(2 * n_downloads) // 3]
        elif n_downloads == 2:
            download_tier1_max = downloads_list[0]
            download_tier2_max = downloads_list[1]
        else:
            download_tier1_max = download_tier2_max = downloads_list[0]

        # Create 3-tier partitions for recency (newer = higher tier)
        n_dates = len(dates_list)
        if n_dates >= 3:
            date_tier1_max = dates_list[n_dates // 3]
            date_tier2_max = dates_list[(2 * n_dates) // 3]
        elif n_dates == 2:
            date_tier1_max = dates_list[0]
            date_tier2_max = dates_list[1]
        else:
            date_tier1_max = date_tier2_max = dates_list[0]

        # Score each candidate
        recommendations = []
        max_coincidences = max(c["coincidences"] for c in candidates)

        for candidate in candidates:
            score = 0.0

            # Downloads score (3 pts max)
            if candidate["downloads"] <= download_tier1_max:
                score += 1.0
            elif candidate["downloads"] <= download_tier2_max:
                score += 2.0
            else:
                score += 3.0

            # Recency score (3 pts max) - newer is better
            if candidate["created_at"] <= date_tier1_max:
                score += 1.0
            elif candidate["created_at"] <= date_tier2_max:
                score += 2.0
            else:
                score += 3.0

            # Coincidences score (4 pts max)
            coincidence_score = (candidate["coincidences"] / max_coincidences) * 4.0
            score += coincidence_score

            recommendations.append(
                {
                    "dataset": candidate["dataset"],
                    "score": round(score, 2),
                    "downloads": candidate["downloads"],
                    "coincidences": candidate["coincidences"],
                }
            )

        # Sort by score (descending) and limit results
        recommendations.sort(key=lambda x: x["score"], reverse=True)

        logger.info(f"Returning {len(recommendations[:limit])} recommendations (sorted by score)")
        for i, rec in enumerate(recommendations[:limit], 1):
            logger.info(f"  {i}. {rec['dataset'].ds_meta_data.title} - Score: {rec['score']}")

        return recommendations[:limit]


class AuthorService(BaseService):
    def __init__(self):
        super().__init__(AuthorRepository())


class DSDownloadRecordService(BaseService):
    def __init__(self):
        super().__init__(DSDownloadRecordRepository())


class DSMetaDataService(BaseService):
    def __init__(self):
        super().__init__(DSMetaDataRepository())

    def update(self, id, **kwargs):
        return self.repository.update(id, **kwargs)

    def filter_by_doi(self, doi: str) -> Optional[DSMetaData]:
        return self.repository.filter_by_doi(doi)


class DSViewRecordService(BaseService):
    def __init__(self):
        super().__init__(DSViewRecordRepository())

    def the_record_exists(self, dataset: DataSet, user_cookie: str):
        return self.repository.the_record_exists(dataset, user_cookie)

    def create_new_record(self, dataset: DataSet, user_cookie: str) -> DSViewRecord:
        return self.repository.create_new_record(dataset, user_cookie)

    def create_cookie(self, dataset: DataSet) -> str:

        user_cookie = request.cookies.get("view_cookie")
        if not user_cookie:
            user_cookie = str(uuid.uuid4())

        existing_record = self.the_record_exists(dataset=dataset, user_cookie=user_cookie)

        if not existing_record:
            self.create_new_record(dataset=dataset, user_cookie=user_cookie)

        return user_cookie


class DOIMappingService(BaseService):
    def __init__(self):
        super().__init__(DOIMappingRepository())

    def get_new_doi(self, old_doi: str) -> str:
        doi_mapping = self.repository.get_new_doi(old_doi)
        if doi_mapping:
            return doi_mapping.dataset_doi_new
        else:
            return None


class SizeService:

    def __init__(self):
        pass

    def get_human_readable_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024**2:
            return f"{round(size / 1024, 2)} KB"
        elif size < 1024**3:
            return f"{round(size / (1024 ** 2), 2)} MB"
        else:
            return f"{round(size / (1024 ** 3), 2)} GB"
