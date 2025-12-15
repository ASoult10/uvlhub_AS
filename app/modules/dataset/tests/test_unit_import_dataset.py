import os
import shutil
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

from app.modules.dataset.model_import_service import ModelImportService


# Fake user to simulate temp folder
class FakeUser:
    def __init__(self):
        self._tmp = tempfile.mkdtemp()

    def temp_folder(self):
        return self._tmp


# =====================================================================
# 1) UNIT TEST – ZIP: Import from ZIP should extract correctly
# =====================================================================
def test_import_from_zip_valid(tmp_path):
    user = FakeUser()

    # Create a temporary ZIP with one .txt file
    zip_file_path = tmp_path / "test.zip"
    txt_path = tmp_path / "file.txt"
    txt_path.write_text("hello world")

    with zipfile.ZipFile(zip_file_path, "w") as z:
        z.write(txt_path, arcname="file.txt")

    # Fake object returned by Flask request.files
    fake_file = MagicMock()
    fake_file.filename = "test.zip"
    fake_file.save = lambda dst: shutil.copy(zip_file_path, dst)

    result = ModelImportService.import_from_zip(fake_file, user)

    assert "error" not in result
    assert os.path.isdir(result["path"])
    assert result["source"] == "zip"
    assert any(f.endswith(".txt") for f in os.listdir(result["path"]))


# =====================================================================
# 2) UNIT TEST – GitHub: ZIP URL is built using default branch
# =====================================================================
@patch("requests.get")
def test_import_from_github_builds_zip_url(mock_get):
    user = FakeUser()

    # Fake GitHub API response for default branch
    mock_get.return_value.status_code = 200
    mock_get.return_value.json = lambda: {"default_branch": "main"}
    mock_get.return_value.content = b"fake zip data"

    mock_zip = MagicMock()
    mock_zip.namelist.return_value = ["folder/file.txt"]

    # Mock ZIP extraction so that the file appears on disk
    with patch("zipfile.ZipFile") as mock_zip_class:
        mock_zip_class.return_value.__enter__.return_value = mock_zip

        # PATCH extractall to create one valid file
        def fake_extractall(path):
            os.makedirs(os.path.join(path, "folder"), exist_ok=True)
            with open(os.path.join(path, "folder", "file.txt"), "w") as f:
                f.write("dummy")

        mock_zip.extractall = fake_extractall

        result = ModelImportService.import_from_github("https://github.com/example/repo", user)

    assert "error" not in result
    assert result["source"] == "github"
    assert os.path.isdir(result["path"])


# =====================================================================
# 3) UNIT TEST – GitHub: Failure when no valid files exist in ZIP
# =====================================================================


@patch("requests.get")
def test_import_from_github_no_valid_files(mock_get):
    user = FakeUser()

    mock_get.return_value.status_code = 200
    mock_get.return_value.content = b"fake zip data"

    mock_zip = MagicMock()
    # No valid files like .uvl / .csv / .json / .txt / .fits
    mock_zip.namelist.return_value = ["folder/README.md"]

    with patch("zipfile.ZipFile") as mock_zip_class:
        mock_zip_class.return_value.__enter__.return_value = mock_zip

        result = ModelImportService.import_from_github("https://github.com/example/repo", user)

    assert "error" in result
