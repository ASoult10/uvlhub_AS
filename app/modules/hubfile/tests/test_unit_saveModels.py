from unittest.mock import MagicMock, patch

import pytest

from app.modules.auth.models import User
from app.modules.hubfile.models import Hubfile
from app.modules.hubfile.repositories import HubfileRepository
from app.modules.hubfile.services import HubfileService


@pytest.fixture
def hubfile_service():
    return HubfileService()


@pytest.fixture
def mock_repository():
    return MagicMock(spec=HubfileRepository)


@pytest.fixture
def sample_user():
    user = MagicMock(spec=User)
    user.id = 1
    return user


@pytest.fixture
def sample_hubfile():
    hubfile = MagicMock(spec=Hubfile)
    hubfile.id = 1
    hubfile.saved_by_users = []
    return hubfile


class TestSavedByUser:
    def test_comprobar_archivo_guardado_verdadero(self, hubfile_service, mock_repository):
        # Verifica que la función devuelve True cuando el archivo está guardado
        # por el usuario
        mock_repository.is_saved_by_user.return_value = True
        hubfile_service.repository = mock_repository

        result = hubfile_service.is_saved_by_user(hubfile_id=1, user_id=1)

        assert result is True
        mock_repository.is_saved_by_user.assert_called_once_with(1, 1)

    def test_comprobar_archivo_guardado_falso(self, hubfile_service, mock_repository):
        # Verifica que la función devuelve False cuando el archivo no está
        # guardado por el usuario
        mock_repository.is_saved_by_user.return_value = False
        hubfile_service.repository = mock_repository

        result = hubfile_service.is_saved_by_user(hubfile_id=1, user_id=1)

        assert result is False
        mock_repository.is_saved_by_user.assert_called_once_with(1, 1)

    def test_con_hubfile_inexistente(self, hubfile_service, mock_repository):
        # Verifica que la función devuelve False cuando el archivo no existe
        mock_repository.is_saved_by_user.return_value = False
        hubfile_service.repository = mock_repository

        result = hubfile_service.is_saved_by_user(hubfile_id=999, user_id=1)

        assert result is False


class TestAddToSaved:
    def test_guardar_archivo(self, hubfile_service, mock_repository):
        # Verifica que se puede agregar un archivo a los guardados del usuario
        # correctamente
        hubfile_service.repository = mock_repository

        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=1)

        mock_repository.add_to_user_saved.assert_called_once_with(1, 1)

    def test_guardar_archivo_guardado(self, hubfile_service, mock_repository):
        # Verifica el comportamiento cuando se intenta agregar un archivo que
        # ya está guardado
        mock_repository.is_saved_by_user.return_value = True
        hubfile_service.repository = mock_repository

        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=1)

        mock_repository.add_to_user_saved.assert_called_once_with(1, 1)

    def test_guardar_archivo_diferente_usuario(self, hubfile_service, mock_repository):
        # Verifica que se puede agregar el mismo archivo para diferentes
        # usuarios
        hubfile_service.repository = mock_repository

        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=2)

        mock_repository.add_to_user_saved.assert_called_once_with(1, 2)


class TestRemoveFromSaved:
    def test_eliminar_archivo(self, hubfile_service, mock_repository):
        # Verifica que se puede eliminar un archivo de los guardados del
        # usuario correctamente
        hubfile_service.repository = mock_repository

        hubfile_service.remove_from_user_saved(hubfile_id=1, user_id=1)

        mock_repository.remove_from_user_saved.assert_called_once_with(1, 1)

    def test_eliminar_archivo_no_guardado(self, hubfile_service, mock_repository):
        # Verifica el comportamiento cuando se intenta eliminar un archivo que
        # no está guardado
        mock_repository.is_saved_by_user.return_value = False
        hubfile_service.repository = mock_repository

        hubfile_service.remove_from_user_saved(hubfile_id=1, user_id=1)

        mock_repository.remove_from_user_saved.assert_called_once_with(1, 1)


class TestGetSavedFilesForUser:
    def test_get_archivos_guardados(self, hubfile_service, mock_repository):
        # Verifica que se obtienen los archivos guardados del usuario
        # correctamente
        mock_files = [MagicMock(spec=Hubfile), MagicMock(spec=Hubfile)]
        mock_repository.get_saved_files_for_user.return_value = mock_files
        hubfile_service.repository = mock_repository

        result = hubfile_service.get_saved_files_for_user(user_id=1)

        assert result == mock_files
        assert len(result) == 2
        mock_repository.get_saved_files_for_user.assert_called_once_with(1)

    def test_no_saved_files(self, hubfile_service, mock_repository):
        # Verifica que se devuelve una lista vacía cuando el usuario no tiene
        # archivos guardados
        mock_repository.get_saved_files_for_user.return_value = []
        hubfile_service.repository = mock_repository

        result = hubfile_service.get_saved_files_for_user(user_id=1)

        assert result == []
        assert len(result) == 0
        mock_repository.get_saved_files_for_user.assert_called_once_with(1)

    def test_get_saved_files_usuario_inexistente(self, hubfile_service, mock_repository):
        # Verifica que se devuelve una lista vacía cuando el usuario no existe
        mock_repository.get_saved_files_for_user.return_value = []
        hubfile_service.repository = mock_repository

        result = hubfile_service.get_saved_files_for_user(user_id=999)

        assert result == []


class TestRutaGuardarArchivo:
    @patch("app.modules.hubfile.routes.current_user")
    @patch("app.modules.hubfile.routes.HubfileService")
    def test_guardar_archivo_usuario_autenticado(self, mock_service, mock_user, hubfile_service):
        # Verifica que un usuario autenticado puede guardar un archivo
        # correctamente
        from app.modules.hubfile.routes import save_file

        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_user.has_role = MagicMock(return_value=False)
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = {"success": True, "message": "File saved successfully", "saved": True}
            result = save_file(1)

            mock_service_instance.add_to_user_saved.assert_called_once_with(1, 1)

    @patch("app.modules.hubfile.routes.current_user")
    def test_guardar_archivo_usuario_no_autenticado(self, mock_user):
        # Verifica que un usuario no autenticado no puede guardar archivos
        from app.modules.hubfile.routes import save_file

        mock_user.is_authenticated = False
        mock_user.has_role = MagicMock(return_value=False)
        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            save_file(1)
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is False
            assert "logged in" in call_args["error"]


class TestRutaEliminarArchivo:
    @patch("app.modules.hubfile.routes.current_user")
    @patch("app.modules.hubfile.routes.HubfileService")
    def test_eliminar_archivo_usuario_autenticado(self, mock_service, mock_user):
        # Verifica que un usuario autenticado puede eliminar un archivo de sus
        # guardados
        from app.modules.hubfile.routes import unsave_file

        mock_user.is_authenticated = True
        mock_user.id = 1
        mock_service_instance = MagicMock()
        mock_service.return_value = mock_service_instance

        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            mock_jsonify.return_value = {"success": True, "message": "File removed successfully", "removed": True}
            result = unsave_file(1)

            mock_service_instance.remove_from_user_saved.assert_called_once_with(1, 1)

    @patch("app.modules.hubfile.routes.current_user")
    def test_eliminar_archivo_usuario_no_autenticado(self, mock_user):
        # Verifica que un usuario no autenticado no puede eliminar archivos
        from app.modules.hubfile.routes import unsave_file

        mock_user.is_authenticated = False

        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            unsave_file(1)
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is False
            assert call_args["error"] == "not_authenticated"


class TestRutaObtenerArchivosGuardados:
    @patch("app.modules.hubfile.routes.current_user")
    @patch("app.modules.hubfile.routes.HubfileService")
    def test_obtener_archivos_guardados_exitosamente(self, mock_service, mock_user):
        # Verifica que se pueden obtener todos los archivos guardados del
        # usuario
        from app.modules.hubfile.routes import get_saved_files

        mock_user.id = 1
        mock_service_instance = MagicMock()
        mock_file1 = MagicMock()
        mock_file1.to_dict.return_value = {"id": 1, "name": "file1.uvl"}
        mock_file2 = MagicMock()
        mock_file2.to_dict.return_value = {"id": 2, "name": "file2.uvl"}

        mock_service_instance.get_saved_files_for_user.return_value = [mock_file1, mock_file2]
        mock_service.return_value = mock_service_instance

        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            get_saved_files()
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is True
            assert len(call_args["files"]) == 2

    @patch("app.modules.hubfile.routes.current_user")
    @patch("app.modules.hubfile.routes.HubfileService")
    def test_obtener_archivos_guardados_lista_vacia(self, mock_service, mock_user):
        # Verifica que se devuelve una lista vacía cuando no hay archivos
        # guardados
        from app.modules.hubfile.routes import get_saved_files

        mock_user.id = 1
        mock_service_instance = MagicMock()
        mock_service_instance.get_saved_files_for_user.return_value = []
        mock_service.return_value = mock_service_instance

        with patch("app.modules.hubfile.routes.jsonify") as mock_jsonify:
            get_saved_files()
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["success"] is True
            assert len(call_args["files"]) == 0
