import os
import shutil
import uuid
from datetime import datetime, timezone, date

from app.modules.auth.models import User
from app.modules.dataset.models import Author, DataSet, DSDownloadRecord, DSMetaData, DSMetrics, PublicationType, Observation
from app.modules.hubfile.models import Hubfile
from core.seeders.BaseSeeder import BaseSeeder
from core.utils.utils import random_datetime

from dotenv import load_dotenv  # isort: skip


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

        # Create DSMetaData instances with new publication types
        publication_types = [
            PublicationType.OBSERVATION_DATA,
            PublicationType.DATA_PAPER,
            PublicationType.JOURNAL_ARTICLE,
            PublicationType.PREPRINT,
        ]

        ds_meta_data_list = [
            DSMetaData(
                deposition_id=1 + i,
                title=f"Sample dataset {i+1}",
                description=f"Description for dataset {i+1}",
                publication_type=publication_types[i % len(publication_types)],
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
                publication_type=PublicationType.TECHNICAL_REPORT,
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
                publication_type=PublicationType.THESIS,
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
                publication_type=PublicationType.SOFTWARE,
                publication_doi="10.1234/dataset7",
                dataset_doi="10.1234/dataset7",
                tags="tag5, tag6",
                ds_metrics_id=seeded_ds_metrics.id,
            )
        )

        seeded_ds_meta_data = self.seed(ds_meta_data_list)

        # Create Observation instances for each DSMetaData
        observations = [
            Observation(
                object_name="M31",
                ra="00:42:44.330",
                dec="+41:16:07.50",
                magnitude=3.44,
                observation_date=date(2024, 1, 15),
                filter_used="V",
                notes="Andromeda Galaxy observation",
                ds_meta_data_id=seeded_ds_meta_data[0].id,
            ),
            Observation(
                object_name="M42",
                ra="05:35:17.300",
                dec="-05:23:28.00",
                magnitude=4.0,
                observation_date=date(2024, 2, 10),
                filter_used="R",
                notes="Orion Nebula observation",
                ds_meta_data_id=seeded_ds_meta_data[1].id,
            ),
            Observation(
                object_name="NGC 7000",
                ra="20:58:47.000",
                dec="+44:19:47.00",
                magnitude=None,
                observation_date=date(2024, 3, 5),
                filter_used="Ha",
                notes="North America Nebula in H-alpha",
                ds_meta_data_id=seeded_ds_meta_data[2].id,
            ),
            Observation(
                object_name="M13",
                ra="16:41:41.440",
                dec="+36:27:35.50",
                magnitude=5.8,
                observation_date=date(2024, 4, 20),
                filter_used="B",
                notes="Hercules Globular Cluster",
                ds_meta_data_id=seeded_ds_meta_data[3].id,
            ),
            Observation(
                object_name="M51",
                ra="13:29:52.700",
                dec="+47:11:43.00",
                magnitude=8.4,
                observation_date=date(2020, 5, 12),
                filter_used="V",
                notes="Whirlpool Galaxy observation",
                ds_meta_data_id=seeded_ds_meta_data[4].id,
            ),
            Observation(
                object_name="M57",
                ra="18:53:35.080",
                dec="+33:01:45.00",
                magnitude=8.8,
                observation_date=date(2024, 6, 8),
                filter_used="OIII",
                notes="Ring Nebula in OIII filter",
                ds_meta_data_id=seeded_ds_meta_data[5].id,
            ),
            Observation(
                object_name="NGC 891",
                ra="02:22:33.400",
                dec="+42:20:57.00",
                magnitude=10.0,
                observation_date=date(2024, 7, 14),
                filter_used="L",
                notes="Edge-on spiral galaxy",
                ds_meta_data_id=seeded_ds_meta_data[6].id,
            ),
        ]

        self.seed(observations)

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

        # Simular descargas de datasets
        download_records = []
        # Dataset 5 (antiguo, muchas descargas) - 10 descargas
        for _ in range(10):
            download_records.append(
                DSDownloadRecord(
                    dataset_id=seeded_datasets[4].id,
                    download_date=datetime(2020, 6, 1, tzinfo=timezone.utc),
                    download_cookie=str(uuid.uuid4()),
                )
            )

        # Dataset 6 (reciente, descargas medias) - 5 descargas
        for _ in range(5):
            download_records.append(
                DSDownloadRecord(
                    dataset_id=seeded_datasets[5].id,
                    download_date=datetime.now(timezone.utc),
                    download_cookie=str(uuid.uuid4()),
                )
            )

        # Dataset 7 (reciente, sin descargas) - 0 descargas

        # Datasets 1-4 (descargas aleatorias para variedad)
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


        # Crear ficheros UVL y asociarlos DIRECTAMENTE al DataSet vía dataset_id
        load_dotenv()  # isort: skip
        working_dir = os.getenv("WORKING_DIR", "")
        src_folder = os.path.join(working_dir, "app", "modules", "dataset", "uvl_examples")

        for i in range(12):
            file_name = f"file{i+1}.uvl"

            # Asignamos 3 ficheros por dataset: 0–2 -> ds0, 3–5 -> ds1, etc.
            dataset = seeded_datasets[i // 3]
            user_id = dataset.user_id

            dest_folder = os.path.join(working_dir, "uploads", f"user_{user_id}", f"dataset_{dataset.id}")
            os.makedirs(dest_folder, exist_ok=True)
            shutil.copy(os.path.join(src_folder, file_name), dest_folder)

            file_path = os.path.join(dest_folder, file_name)

            uvl_file = Hubfile(
                name=file_name,
                checksum=f"checksum{i+1}",
                size=os.path.getsize(file_path),
                dataset_id=dataset.id,
            )
            self.seed([uvl_file])
