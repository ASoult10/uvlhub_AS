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
    user_id=1,
):
    if authors is None:
        authors = [
            Author(name="John Doe", affiliation="Uni Madrid", orcid="0000-0000-0000-0001")
        ]

    ds = DataSet(created_at=datetime.fromisoformat(created_at), user_id=user_id)
    meta = DSMetaData(
        title=title,
        description=description,
        tags=tags,
        publication_type=publication_type,
        dataset_doi="doi:123"
    )

    for a in authors:
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

    author_oppenheimer = Author(id=1, name="J. Robert Oppenheimer",
                                affiliation="Caltech", orcid="0000-0000-0000-0002")
    author_hans_landa = Author(id=2, name="Hans Landa", affiliation="Uni Vienna", orcid="0000-0000-0000-0003")
    author_mr_pink = Author(id=3, name="Mr Pink", affiliation="Uni Los Angeles", orcid="0000-0000-0000-0004")
    author_jules = Author(id=4, name="Jules", affiliation="Uni Los Angeles", orcid="0000-0000-0000-0005")
    session.add(author_oppenheimer)
    session.add(author_hans_landa)
    session.add(author_mr_pink)
    session.add(author_jules)
    session.commit()

    # Crear datasets con user_id único para cada uno
    create_dataset(session)
    create_dataset(session, title="Beta dataset",
                   description="Another description",
                   tags="chemistry,geo",
                   created_at="2024-01-15",
                   user_id=2)
    create_dataset(session, title="Gamma dataset",
                   description="Meridian rocks",
                   tags="geo",
                   authors=[author_jules],
                   created_at="2024-02-27",
                   user_id=3)
    create_dataset(session, title="Epsilon dataset",
                   description="Nombre del cuarto de libra con queso en Paris",
                   tags="medicine,geo",
                   authors=[author_hans_landa],
                   created_at="2024-06-05",
                   user_id=4)
    create_dataset(session, title="Delta dataset",
                   description="Unrelated description",
                   tags="history,art",
                   authors=[author_mr_pink],
                   created_at="2024-10-10",
                   user_id=5)
    create_dataset(session, title="Sigma dataset",
                   description="Nuclear fusion",
                   tags="physics,history",
                   authors=[author_oppenheimer],
                   created_at="2025-10-31",
                   publication_type=PublicationType.DATA_PAPER,
                   user_id=6)

    yield session

    session.close()
    engine.dispose()


@pytest.fixture
def repository(db_session):
    repo = ExploreRepository()
    repo.model.query = db_session.query(repo.model)
    return repo


def test_filter_by_text_query_title(repository):
    # Titulo
    search = "alpha"
    results = repository.filter(query=search)
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Alpha dataset"


def test_filter_by_text_query_description(repository):
    # Descripcion
    search = "Nuclear"
    results = repository.filter(query=search)
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Sigma dataset"


def test_filter_by_text_query_author_name(repository):
    # Nombre de autor
    search = "Oppenheimer"
    results = repository.filter(query=search)
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Sigma dataset"


def test_filter_by_text_query_author_affiliation(repository):
    # Afiliacion de autor
    search = "Vienna"
    results = repository.filter(query=search)
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Epsilon dataset"


def test_filter_by_text_query_author_orcid(repository):
    # ORCID de autor
    search = "0000-0000-0000-0005"
    results = repository.filter(query=search)
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Gamma dataset"


def test_filter_by_text_query_tags(repository):
    # Tags
    search = "history"
    results = repository.filter(query=search)
    assert len(results) == 2
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" not in titles
    assert "Beta dataset" not in titles
    assert "Gamma dataset" not in titles
    assert "Epsilon dataset" not in titles
    assert "Delta dataset" in titles
    assert "Sigma dataset" in titles


def test_filter_by_date_after(repository):
    # Fecha despues de 2025-01-01
    results = repository.filter(date_after="2025-01-01")
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Sigma dataset"


def test_filter_by_date_before(repository):
    # Fecha antes de 2024-02-01
    results = repository.filter(date_before="2024-02-01")
    assert len(results) == 2
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" in titles
    assert "Beta dataset" in titles
    assert "Gamma dataset" not in titles
    assert "Epsilon dataset" not in titles
    assert "Delta dataset" not in titles
    assert "Sigma dataset" not in titles


def test_filter_by_date_range(repository):
    # Rango de fechas
    results = repository.filter(date_after="2024-01-01", date_before="2024-12-31")
    assert len(results) == 5
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" in titles
    assert "Beta dataset" in titles
    assert "Gamma dataset" in titles
    assert "Epsilon dataset" in titles
    assert "Delta dataset" in titles
    assert "Sigma dataset" not in titles


def test_filter_by_author_multiple(repository):
    # Varios resultados
    results = repository.filter(author="John Doe")
    assert len(results) == 2
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" in titles
    assert "Beta dataset" in titles
    assert "Gamma dataset" not in titles
    assert "Epsilon dataset" not in titles
    assert "Delta dataset" not in titles
    assert "Sigma dataset" not in titles


def test_filter_by_author_single(repository):
    # Un unico resultado
    results = repository.filter(author="Hans Landa")
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Epsilon dataset"


def test_filter_by_tags_single(repository):
    # Un tag
    results = repository.filter(tags=["geo"])
    assert len(results) == 4
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" in titles
    assert "Beta dataset" in titles
    assert "Gamma dataset" in titles
    assert "Epsilon dataset" in titles
    assert "Delta dataset" not in titles
    assert "Sigma dataset" not in titles


def test_filter_by_tags_multiple(repository):
    # Varios tags
    results = repository.filter(tags=["history", "art"])
    assert len(results) == 2
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" not in titles
    assert "Beta dataset" not in titles
    assert "Gamma dataset" not in titles
    assert "Epsilon dataset" not in titles
    assert "Delta dataset" in titles
    assert "Sigma dataset" in titles


def test_filter_by_publication_type_single(repository):
    # Tipo de publicacion DATA_PAPER
    results = repository.filter(publication_type="data_paper")
    assert len(results) == 1
    assert results[0].ds_meta_data.title == "Sigma dataset"


def test_filter_by_publication_type_multiple(repository):
    # Tipo de publicacion JOURNAL_ARTICLE
    results = repository.filter(publication_type="journal_article")
    assert len(results) == 5
    titles = [ds.ds_meta_data.title for ds in results]
    assert "Alpha dataset" in titles
    assert "Beta dataset" in titles
    assert "Gamma dataset" in titles
    assert "Epsilon dataset" in titles
    assert "Delta dataset" in titles
    assert "Sigma dataset" not in titles
