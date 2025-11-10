import os
import shutil
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

from app.modules.auth.models import User
from app.modules.dataset.models import (
    Author,
    DSDownloadRecord,
    DataSet,
    DSMetaData,
    DSMetrics,
    PublicationType,
)
from app.modules.featuremodel.models import FMMetaData, FeatureModel
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder
from core.utils.utils import random_datetime


class DataSetSeeder(BaseSeeder):

    priority = 2  # Lower priority

    def run(self):
        # Retrieve users
        user1 = User.query.filter_by(email="user1@example.com").first()
        user2 = User.query.filter_by(email="user2@example.com").first()

        if not user1 or not user2:
            raise Exception("Users not found. Please seed users first.")

        # Create DSMetrics instance
        ds_metrics = DSMetrics(number_of_models="5", number_of_features="50")
        seeded_ds_metrics = self.seed([ds_metrics])[0]

        # Create DSMetaData instances
        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i+1}",
                description=f"Description for dataset {i+1}",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi=f"10.1234/dataset{i+1}",
                dataset_doi=f"10.1234/dataset{i+1}",
                tags="tag1, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
            for i in range(4)
        ]

        # Additional DSMetaData with specific tags and author for testing Recommender System
        # ID5: Different tag same author, old, 1st downloads.
        ds_meta_data_list.append(
            DSMetaData(
                deposition_id=5,
                title="Dataset with tag3,tag4 and author 1",
                description="Description for dataset with specific tags and author",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset5",
                dataset_doi="10.1234/dataset5",
                tags="tag3, tag4",
                ds_metrics_id=seeded_ds_metrics.id,
            )
        )

        # ID6: One coincidence tag same author, recent, middle road downloads.
        ds_meta_data_list.append(
            DSMetaData(
                deposition_id=6,
                title="Dataset with author 1",
                description="Description for dataset with specific tags and author",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset6",
                dataset_doi="10.1234/dataset6",
                tags="tag3, tag2",
                ds_metrics_id=seeded_ds_metrics.id,
            )
        )

        # ID7: Different tag different author, recent, no downloads, shouldnt show.
        ds_meta_data_list.append(
            DSMetaData(
                deposition_id=7,
                title="Dataset with tag5 and author 7",
                description="Description for dataset with specific tags and author",
                publication_type=PublicationType.DATA_MANAGEMENT_PLAN,
                publication_doi="10.1234/dataset7",
                dataset_doi="10.1234/dataset7",
                tags="tag5, tag6",
                ds_metrics_id=seeded_ds_metrics.id,
            )
        )

        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create Author instances and associate with DSMetaData
        authors = [
            Author(
                name=f"Author {i+1}",
                affiliation=f"Affiliation {i+1}",
                orcid=f"0000-0000-0000-000{i}",
                ds_meta_data_id=seeded_ds_meta_data[i % 4].id,
            )
            for i in range(4)
        ]

        # Authors for testing datasets id 5 to 7
        authors.append(
            Author(
                name="Author 1",
                affiliation="Affiliation 1",
                orcid="0000-0000-0000-0001",
                ds_meta_data_id=seeded_ds_meta_data[4].id,
            )
        )
        authors.append(
            Author(
                name="Author 1",
                affiliation="Affiliation 1",
                orcid="0000-0000-0000-0001",
                ds_meta_data_id=seeded_ds_meta_data[5].id,
            )
        )
        authors.append(
            Author(
                name="Author 7",
                affiliation="Affiliation 7",
                orcid="0000-0000-0000-0007",
                ds_meta_data_id=seeded_ds_meta_data[6].id,
            )
        )

        self.seed(authors)

        # Create DataSet instances
        datasets = [
            DataSet(
                user_id=user1.id if i % 2 == 0 else user2.id,
                ds_meta_data_id=seeded_ds_meta_data[i].id,
                created_at=random_datetime(
                    datetime(2020, 1, 1, tzinfo=timezone.utc),
                    datetime.now(timezone.utc),
                ),
            )
            for i in range(4)
        ]

        datasets.append(
            DataSet(
                user_id=user1.id,
                ds_meta_data_id=seeded_ds_meta_data[4].id,
                created_at=datetime(2020, 1, 1, tzinfo=timezone.utc),  # Old date
            )
        )
        datasets.append(
            DataSet(
                user_id=user1.id,
                ds_meta_data_id=seeded_ds_meta_data[5].id,
                created_at=datetime.now(timezone.utc),  # Recent date
            )
        )
        datasets.append(
            DataSet(
                user_id=user2.id,
                ds_meta_data_id=seeded_ds_meta_data[6].id,
                created_at=datetime.now(timezone.utc),  # Recent date
            )
        )

        seeded_datasets = self.seed(datasets)
        # Finally we going to add a new seeder, for download count.
        # To simulate download for the different datasets.

        download_records = []
        for _ in range(10):
            download_records.append(
                DSDownloadRecord(
                    dataset_id=seeded_datasets[4].id,
                    download_date=datetime(2020, 6, 1, tzinfo=timezone.utc),
                    download_cookie=str(uuid.uuid4()),
                )
            )

        # Dataset 6 (recent, medium downloads) - 5 downloads
        for _ in range(5):
            download_records.append(
                DSDownloadRecord(
                    dataset_id=seeded_datasets[5].id,
                    download_date=datetime.now(timezone.utc),
                    download_cookie=str(uuid.uuid4()),
                )
            )

        # Dataset 7 (recent, no downloads) - 0 downloads (skip)

        # Datasets 1-4 (random downloads for variety)
        for i in range(4):
            for _ in range((i + 1) * 2):  # 2, 4, 6, 8 downloads
                download_records.append(
                    DSDownloadRecord(
                        dataset_id=seeded_datasets[i].id,
                        download_date=random_datetime(
                            datetime(2021, 1, 1, tzinfo=timezone.utc),
                            datetime.now(timezone.utc),
                        ),
                        download_cookie=str(uuid.uuid4()),
                    )
                )

        self.seed(download_records)

        # Assume there are 12 UVL files, create corresponding FMMetaData and FeatureModel
        fm_meta_data_list = [
            FMMetaData(
                uvl_filename=f"file{i+1}.uvl",
                title=f"Feature Model {i+1}",
                description=f"Description for feature model {i+1}",
                publication_type=PublicationType.SOFTWARE_DOCUMENTATION,
                publication_doi=f"10.1234/fm{i+1}",
                tags="tag1, tag2",
                uvl_version="1.0",
            )
            for i in range(12)
        ]
        seeded_fm_meta_data = self.seed(fm_meta_data_list)

        # Create Author instances and associate with FMMetaData
        fm_authors = [
            Author(
                name=f"Author {i+5}",
                affiliation=f"Affiliation {i+5}",
                orcid=f"0000-0000-0000-000{i+5}",
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        self.seed(fm_authors)

        feature_models = [
            FeatureModel(
                data_set_id=seeded_datasets[i // 3].id,
                fm_meta_data_id=seeded_fm_meta_data[i].id,
            )
            for i in range(12)
        ]
        seeded_feature_models = self.seed(feature_models)

        # Create files, associate them with FeatureModels and copy files
        load_dotenv()
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(
            working_dir, "app", "modules", "dataset", "uvl_examples"
        )
        for i in range(12):
            file_name = f"file{i+1}.uvl"
            feature_model = seeded_feature_models[i]
            dataset = next(
                ds for ds in seeded_datasets if ds.id == feature_model.data_set_id
            )
            user_id = dataset.user_id

            dest_folder = os.path.join(
                working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}"
            )
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            uvl_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i+1}",
                size=os.path.getsize(file_path),
                feature_model_id=feature_model.id,
            )
            self.seed([uvl_file])
