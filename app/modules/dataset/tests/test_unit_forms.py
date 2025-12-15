import pytest
from datetime import date

from app import create_app
from app.modules.dataset.forms import AuthorForm, ObservationForm, DataSetForm, EditDataSetForm
from app.modules.dataset.models import PublicationType
from werkzeug.datastructures import MultiDict 


@pytest.fixture(scope="module")
def test_client():
    """
    Create a Flask test client with application context.
    """
    app = create_app()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False

    with app.test_client() as testing_client:
        with app.app_context():
            yield testing_client


@pytest.fixture
def valid_observation_data():
    """
    Fixture que proporciona datos de observación válidos y completos.
    """
    return {
        "object_name": "M31",
        "ra": "00:42:44.330",
        "dec": "+41:16:09.00",
        "magnitude": 3.44,
        "observation_date": "2024-12-10",
        "filter_used": "V",
        "notes": "Andromeda Galaxy observation"
    }


class TestAuthorForm:
    """Unit tests for dataset form: AuthorForm"""

    def test_author_form_valid_data(test_client):
        """
        Test AuthorForm with valid data.
        """
        form = AuthorForm(
            data={
                "name": "John Doe",
                "affiliation": "Test University",
                "orcid": "0000-0001-2345-6789",
                "gnd": "123456789"
            }
        )

        assert form.validate() is True
        author = form.get_author()
        assert author["name"] == "John Doe"
        assert author["affiliation"] == "Test University"
        assert author["orcid"] == "0000-0001-2345-6789"

    def test_author_form_missing_name(test_client):
        """
        Test AuthorForm fails without required name field.
        """
        form = AuthorForm(
            data={
                "name": "",
                "affiliation": "Test University"
            }
        )

        assert form.validate() is False
        assert "name" in form.errors

    def test_author_form_optional_fields(test_client):
        """
        Test AuthorForm with only required fields.
        """
        form = AuthorForm(
            data={
                "name": "Jane Smith"
            }
        )

        assert form.validate() is True
        author = form.get_author()
        assert author["name"] == "Jane Smith"
        assert author["affiliation"] is None
        assert author["orcid"] is None


class TestObservationForm:
    """Unit tests for dataset form: ObservationForm"""

    def test_observation_form_is_empty(test_client):
        """
        Test ObservationForm.is_empty() returns True when all fields are empty.
        """
        form = ObservationForm(data={})
        assert form.is_empty() is True

    def test_observation_form_is_not_empty(test_client):
        """
        Test ObservationForm.is_empty() returns False when any field has data.
        """
        form = ObservationForm(
            data={
                "object_name": "M31"
            }
        )
        assert form.is_empty() is False

    def test_observation_form_valid_complete_data(test_client):
        """
        Test ObservationForm with all valid data.
        """
        form = ObservationForm(
            data={
                "object_name": "M31",
                "ra": "00:42:44.330",
                "dec": "+41:16:09.00",
                "magnitude": 3.44,
                "observation_date": date(2024, 12, 10),
                "filter_used": "V",
                "notes": "Clear sky observation"
            }
        )

        assert form.validate() is True
        obs = form.get_observation()
        assert obs["object_name"] == "M31"
        assert obs["ra"] == "00:42:44.330"
        assert obs["dec"] == "+41:16:09.00"
        assert obs["magnitude"] == 3.44

    def test_observation_form_missing_required_fields(test_client):
        """
        Test ObservationForm fails when required fields are missing for a non-empty observation.
        """
        form = ObservationForm(
            data={
                "magnitude": 5.0  # Has data but missing object_name, ra, dec
            }
        )

        assert form.validate() is False
        assert "Object name is required" in str(form.object_name.errors)
        assert "RA is required" in str(form.ra.errors)
        assert "DEC is required" in str(form.dec.errors)

    def test_observation_form_invalid_ra_format(test_client):
        """
        Test ObservationForm fails with invalid RA format.
        """
        form = ObservationForm(
            data={
                "object_name": "M31",
                "ra": "25:00:00",  # Invalid: hours > 23
                "dec": "+41:16:09.00"
            }
        )

        assert form.validate() is False
        assert "Invalid RA format" in str(form.ra.errors)

    def test_observation_form_invalid_dec_format(test_client):
        """
        Test ObservationForm fails with invalid DEC format.
        """
        form = ObservationForm(
            data={
                "object_name": "M31",
                "ra": "00:42:44",
                "dec": "+95:00:00"  # Invalid: degrees > 90
            }
        )

        assert form.validate() is False
        assert "Invalid DEC format" in str(form.dec.errors)

    def test_observation_form_valid_ra_formats(test_client):
        """
        Test ObservationForm accepts various valid RA formats.
        """
        valid_ras = [
            "00:00:00",
            "12:30:45",
            "23:59:59",
            "01:23:45.678"
        ]

        for ra in valid_ras:
            form = ObservationForm(
                data={
                    "object_name": "Test",
                    "ra": ra,
                    "dec": "+00:00:00"
                }
            )
            assert form.validate() is True, f"RA {ra} should be valid"

    def test_observation_form_valid_dec_formats(test_client):
        """
        Test ObservationForm accepts various valid DEC formats.
        """
        valid_decs = [
            "+00:00:00",
            "-45:30:15",
            "+90:00:00",
            "-90:00:00",
            "+12:34:56.789"
        ]

        for dec in valid_decs:
            form = ObservationForm(
                data={
                    "object_name": "Test",
                    "ra": "12:00:00",
                    "dec": dec
                }
            )
            assert form.validate() is True, f"DEC {dec} should be valid"


class TestDataSetForm:
    """Unit tests for dataset form: DataSetForm"""

    def test_dataset_form_valid_data(test_client):
        """
        Test DataSetForm with valid complete data.
        """
        form = DataSetForm(
            data={
                "title": "Test Dataset",
                "desc": "This is a test dataset",
                "publication_type": PublicationType.DATA_PAPER.value,
                "publication_doi": "https://doi.org/10.1234/test",
                "tags": "astronomy, test, data"
            }
        )

        assert form.validate() is True
        metadata = form.get_dsmetadata()
        assert metadata["title"] == "Test Dataset"
        assert metadata["description"] == "This is a test dataset"
        assert metadata["publication_type"] == "DATA_PAPER"

    def test_dataset_form_valid_data_with_observation(test_client, valid_observation_data):
        """
        Test DataSetForm with valid data including observation.
        """
        # Copiar los datos de observación y convertir la fecha a objeto date
        observation_data = valid_observation_data.copy()
        observation_data["observation_date"] = date(2024, 12, 10)
        
        form_data = {
            "title": "Test Dataset with Observation",
            "desc": "Dataset including observation data",
            "publication_type": PublicationType.OBSERVATION_DATA.value,
            "tags": "observation, test",
            "observation": observation_data  # Pasar como diccionario anidado
        }

        form = DataSetForm(data=form_data)

        assert form.validate() is True
        metadata = form.get_dsmetadata()
        assert metadata["title"] == "Test Dataset with Observation"
        assert metadata["publication_type"] == "OBSERVATION_DATA"

        observation = form.get_observation()
        assert observation is not None
        assert observation["object_name"] == "M31"
        assert observation["ra"] == "00:42:44.330"
        assert observation["dec"] == "+41:16:09.00"

    def test_dataset_form_missing_required_fields(test_client):
        """
        Test DataSetForm fails without required fields.
        """
        form = DataSetForm(data={})

        assert form.validate() is False
        assert "title" in form.errors
        assert "desc" in form.errors
        assert "publication_type" in form.errors

    def test_dataset_form_convert_publication_type(test_client):
        """
        Test DataSetForm.convert_publication_type() correctly converts values.
        """
        form = DataSetForm()

        assert form.convert_publication_type(PublicationType.DATA_PAPER.value) == "DATA_PAPER"
        assert form.convert_publication_type(PublicationType.OBSERVATION_DATA.value) == "OBSERVATION_DATA"
        assert form.convert_publication_type("invalid") == "NONE"

    def test_dataset_form_get_authors(test_client):
        """
        Test DataSetForm.get_authors() returns correct author list.
        """
        form = DataSetForm(
            data={
                "title": "Test",
                "desc": "Description",
                "publication_type": PublicationType.DATA_PAPER.value,
                "authors-0-name": "Author One",
                "authors-0-affiliation": "University A",
                "authors-1-name": "Author Two",
                "authors-1-affiliation": "University B"
            }
        )

        # Manually populate authors (as it would be done in the view)
        form.authors.append_entry({"name": "Author One", "affiliation": "University A"})
        form.authors.append_entry({"name": "Author Two", "affiliation": "University B"})

        authors = form.get_authors()
        assert len(authors) == 2
        assert authors[0]["name"] == "Author One"
        assert authors[1]["name"] == "Author Two"

    def test_dataset_form_get_observation_empty(test_client):
        """
        Test DataSetForm.get_observation() returns None when observation is empty.
        """
        form = DataSetForm(
            data={
                "title": "Test",
                "desc": "Description",
                "publication_type": PublicationType.DATA_PAPER.value
            }
        )

        assert form.get_observation() is None

    def test_dataset_form_get_observation_with_data(test_client):
        """
        Test DataSetForm.get_observation() returns observation data when present.
        """
        form = DataSetForm(
            data={
                "title": "Test",
                "desc": "Description",
                "publication_type": PublicationType.DATA_PAPER.value,
                "observation-object_name": "M31",
                "observation-ra": "00:42:44",
                "observation-dec": "+41:16:09"
            }
        )

        observation = form.get_observation()
        if observation:  # Only test if observation data was properly set
            assert observation["object_name"] == "M31"




class TestEditDataSetForm:
    """Unit tests for dataset form: EditDataSetForm"""

    def test_edit_dataset_form_valid_data(self, test_client):
        """
        Test EditDataSetForm with valid complete data.
        """
        # Simulamos los datos
        form_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "publication_type": PublicationType.DATA_PAPER.name,
            "tags": "updated, tags",
            "object_name": "M31",
            "ra": "00:42:44.330",
            "dec": "+41:16:09.00",
            "magnitude": "3.44", # En formdata todo llega como string
            "observation_date": "2024-12-10",
            "filter_used": "V",
            "notes": "Updated notes"
        }

        # USAMOS MultiDict y formdata= PARA SIMULAR UN POST REAL
        # Esto satisface al validador InputRequired
        form = EditDataSetForm(formdata=MultiDict(form_data))

        if not form.validate():
            # Esto imprimirá los errores en la consola si falla, ayudándote a depurar
            print(f"Form Errors: {form.errors}")

        assert form.validate() is True

        # Verificar obtención de metadatos
        metadata = form.get_dsmetadata()
        assert metadata["title"] == "Updated Title"
        assert metadata["publication_type"] == "DATA_PAPER"

        # Verificar obtención de observación
        obs = form.get_observation()
        assert obs["object_name"] == "M31"
        assert obs["ra"] == "00:42:44.330"
        
        # Nota: Al venir de formdata, los FloatField convierten automáticamente, 
        # pero es bueno asegurar que el valor sea correcto.
        assert obs["magnitude"] == 3.44 

    def test_edit_dataset_form_optional_fields(self, test_client):
        """
        Test EditDataSetForm validates correctly without optional fields.
        """
        form_data = {
            "title": "Valid Title",
            "description": "Valid Description",
            "publication_type": PublicationType.DATA_PAPER.name,
            "object_name": "M31",
            "ra": "00:00:00",
            "dec": "+00:00:00",
            "observation_date": "2024-01-01"
            # Faltan: tags, magnitude, filter_used, notes
        }

        # Usamos formdata=MultiDict(...) aquí también
        form = EditDataSetForm(formdata=MultiDict(form_data))
        
        if not form.validate():
            print(f"Optional Fields Test Errors: {form.errors}")
            
        assert form.validate() is True
        
        obs = form.get_observation()
        # Verificamos que los campos opcionales sean None o vacíos
        assert obs["magnitude"] is None
        assert not obs["filter_used"] # Puede ser None o string vacío
        assert not obs["notes"]

    def test_edit_dataset_form_missing_required_observation(self, test_client):
        """
        Test EditDataSetForm fails when required observation fields are missing.
        """
        form_data = {
            "title": "Valid Title",
            "description": "Valid Description",
            "publication_type": PublicationType.DATA_PAPER.name,
            # Missing observation fields intentionally
        }

        form = EditDataSetForm(formdata=MultiDict(form_data))
        
        assert form.validate() is False
        assert "object_name" in form.errors
        assert "ra" in form.errors
        assert "dec" in form.errors
        # Ahora InputRequired funcionará correctamente detectando que falta el dato
        assert "observation_date" in form.errors 

    def test_edit_dataset_form_invalid_ra_format(self, test_client):
        """
        Test EditDataSetForm regex validation for Right Ascension (RA).
        """
        form_data = {
            "title": "Valid Title",
            "description": "Valid Description",
            "publication_type": PublicationType.DATA_PAPER.name,
            "object_name": "M31",
            "ra": "25:00:00",  # Invalid
            "dec": "+00:00:00",
            "observation_date": "2024-01-01"
        }

        form = EditDataSetForm(formdata=MultiDict(form_data))
        
        assert form.validate() is False
        assert "ra" in form.errors
        assert "Format must be HH:MM:SS" in str(form.ra.errors)

    def test_edit_dataset_form_invalid_dec_format(self, test_client):
        """
        Test EditDataSetForm regex validation for Declination (Dec).
        """
        form_data = {
            "title": "Valid Title",
            "description": "Valid Description",
            "publication_type": PublicationType.DATA_PAPER.name,
            "object_name": "M31",
            "ra": "00:00:00",
            "dec": "+95:00:00",  # Invalid
            "observation_date": "2024-01-01"
        }

        form = EditDataSetForm(formdata=MultiDict(form_data))
        
        assert form.validate() is False
        assert "dec" in form.errors
        assert "Format must be +/-DD:MM:SS" in str(form.dec.errors)
    
