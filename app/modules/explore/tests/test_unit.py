import pytest
from datetime import datetime
from app.modules.explore.repositories import ExploreRepository
from app.modules.dataset.models import DataSet, DSMetaData, Author, PublicationType
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session


def create_dataset(
    session,
    title="Alpha dataset",
    description="Some interesting description",
    tags="bio,geo",
    authors=None,
    created_at="2024-01-10",
    publication_type=PublicationType.JOURNAL_ARTICLE,
):
    if authors is None:
        authors = [
            Author(name="John Doe", affiliation="Uni Madrid", orcid="0000-0000-0000-0001")
        ]

    ds = DataSet(created_at=datetime.fromisoformat(created_at))
    meta = DSMetaData(
        title=title,
        description=description,
        tags=tags,
        publication_type=publication_type.name,
        dataset_doi="doi:123"
    )

    for a in authors:
        session.add(a)
        meta.authors.append(a)

    session.add(meta)
    ds.ds_meta_data = meta
    session.add(ds)
    session.commit()
    return ds


# Base de datos de prueba en memoria
@pytest.fixture(scope="module")
def db_session():
    engine = create_engine("sqlite:///:memory:")

    DataSet.metadata.create_all(engine)
    DSMetaData.metadata.create_all(engine)
    Author.metadata.create_all(engine)

    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()

    # Autores de prueba
    author_oppenheimer = Author(name="J. Robert Oppenheimer",
                                affiliation="Caltech", orcid="0000-0000-0000-002")
    author_hans_landa = Author(name="Hans Landa", affiliation="Uni Vienna", orcid="0000-0000-0000-003")
    author_mr_pink = Author(name="Mr. Pink", affiliation="Uni Los Angeles", orcid="0000-0000-0000-004")
    author_jules = Author(name="Jules", affiliation="Uni Los Angeles", orcid="0000-0000-0000-005")

    # Crear dataset prueba estandar
    create_dataset(session)
    # Datsets adicionales
    create_dataset(session, title="Beta dataset",
                   description="Another description",
                   tags="chemistry,geo",
                   created_at="2024-01-15")
    create_dataset(session, title="Gamma dataset",
                   description="Meridian rocks",
                   tags="geo",
                   authors=[
                       author_jules,
                       author_mr_pink
                   ],
                   created_at="2024-02-27")
    create_dataset(session, title="Epsilon dataset",
                   description="Nombre del cuarto de libra con queso en Paris",
                   tags="medicine,geo",
                   authors=[
                       author_hans_landa,
                       author_mr_pink
                   ],
                   created_at="2024-06-05")
    create_dataset(session, title="Delta dataset",
                   description="Unrelated description",
                   tags="history,art",
                   authors=[author_mr_pink],
                   created_at="2025-03-30")
    create_dataset(session, title="Delta dataset",
                   description="Nuclear fusion",
                   tags="physics,history",
                   authors=[author_oppenheimer],
                   created_at="2025-10-31")

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def repository(db_session):
    repo = ExploreRepository()
    repo.session = db_session
    return repo
