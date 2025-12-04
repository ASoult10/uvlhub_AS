import pytest
from unittest.mock import MagicMock, patch
from app.modules.hubfile.services import HubfileService
from app.modules.hubfile.repositories import HubfileRepository
from app.modules.hubfile.models import Hubfile
from app.modules.auth.models import User


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
        # Verifica que la función devuelve True cuando el archivo está guardado por el usuario
        mock_repository.is_saved_by_user.return_value = True
        hubfile_service.repository = mock_repository
        
        result = hubfile_service.is_saved_by_user(hubfile_id=1, user_id=1)
        
        assert result is True
        mock_repository.is_saved_by_user.assert_called_once_with(1, 1)

    def test_comprobar_archivo_guardado_falso(self, hubfile_service, mock_repository):
        # Verifica que la función devuelve False cuando el archivo no está guardado por el usuario
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
        # Verifica que se puede agregar un archivo a los guardados del usuario correctamente
        hubfile_service.repository = mock_repository
        
        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=1)
        
        mock_repository.add_to_user_saved.assert_called_once_with(1, 1)

    def test_guardar_archivo_guardado(self, hubfile_service, mock_repository):
        # Verifica el comportamiento cuando se intenta agregar un archivo que ya está guardado
        mock_repository.is_saved_by_user.return_value = True
        hubfile_service.repository = mock_repository
        
        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=1)
        
        mock_repository.add_to_user_saved.assert_called_once_with(1, 1)

    def test_guardar_archivo_diferente_usuario(self, hubfile_service, mock_repository):
        # Verifica que se puede agregar el mismo archivo para diferentes usuarios
        hubfile_service.repository = mock_repository
        
        hubfile_service.add_to_user_saved(hubfile_id=1, user_id=2)
        
        mock_repository.add_to_user_saved.assert_called_once_with(1, 2)


class TestRemoveFromSaved:
    def test_eliminar_archivo(self, hubfile_service, mock_repository):
        # Verifica que se puede eliminar un archivo de los guardados del usuario correctamente
        hubfile_service.repository = mock_repository
        
        hubfile_service.remove_from_user_saved(hubfile_id=1, user_id=1)
        
        mock_repository.remove_from_user_saved.assert_called_once_with(1, 1)

    def test_eliminar_archivo_no_guardado(self, hubfile_service, mock_repository):
        # Verifica el comportamiento cuando se intenta eliminar un archivo que no está guardado
        mock_repository.is_saved_by_user.return_value = False
        hubfile_service.repository = mock_repository
        
        hubfile_service.remove_from_user_saved(hubfile_id=1, user_id=1)
        
        mock_repository.remove_from_user_saved.assert_called_once_with(1, 1)


class TestGetSavedFilesForUser:
    def test_get_archivos_guardados(self, hubfile_service, mock_repository):
        # Verifica que se obtienen los archivos guardados del usuario correctamente
        mock_files = [MagicMock(spec=Hubfile), MagicMock(spec=Hubfile)]
        mock_repository.get_saved_files_for_user.return_value = mock_files
        hubfile_service.repository = mock_repository
        
        result = hubfile_service.get_saved_files_for_user(user_id=1)
        
        assert result == mock_files
        assert len(result) == 2
        mock_repository.get_saved_files_for_user.assert_called_once_with(1)

    def test_no_saved_files(self, hubfile_service, mock_repository):
        # Verifica que se devuelve una lista vacía cuando el usuario no tiene archivos guardados
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