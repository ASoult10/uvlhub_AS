import os
import zipfile
import tempfile
import shutil
import logging
import requests

logger = logging.getLogger(__name__)


class ModelImportService:

    # ============================================
    #   PROTEGER PATH (ZIP SLIP)
    # ============================================
    @staticmethod
    def _is_safe_path(base_path, target_path):
        return os.path.realpath(target_path).startswith(os.path.realpath(base_path))

    # ============================================
    #   IMPORTAR DESDE ZIP SUBIDO
    # ============================================
    @staticmethod
    def import_from_zip(zip_file, current_user):

        if not zip_file.filename.lower().endswith(".zip"):
            return {"error": "Uploaded file is not a ZIP file."}

        base_temp = current_user.temp_folder()

        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)
        os.makedirs(base_temp, exist_ok=True)

        zip_path = os.path.join(base_temp, zip_file.filename)
        zip_file.save(zip_path)

        extract_path = os.path.join(base_temp, "imported")
        os.makedirs(extract_path, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                if len(z.namelist()) == 0:
                    return {"error": "ZIP is empty."}

                for member in z.namelist():
                    member_path = os.path.join(extract_path, member)
                    if not ModelImportService._is_safe_path(extract_path, member_path):
                        return {"error": f"Unsafe ZIP entry: {member}"}

                z.extractall(extract_path)

        except Exception as e:
            return {"error": f"Error extracting ZIP: {e}"}

        if not os.listdir(extract_path):
            return {"error": "ZIP extracted but contains no files."}

        logger.info(f"[IMPORT] ZIP extracted successfully at: {extract_path}")

        try:
            os.remove(zip_path)
        except:
            pass

        return {"path": extract_path, "source": "zip"}

    # ============================================
    #   OBTENER RAMA POR DEFECTO DESDE GITHUB API
    # ============================================
    @staticmethod
    def _get_default_branch(user, repo):
        api_url = f"https://api.github.com/repos/{user}/{repo}"
        try:
            r = requests.get(api_url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                return data.get("default_branch", "main")
        except:
            pass
        return "main"

    # ============================================
    #   IMPORTAR DESDE GITHUB
    # ============================================
    @staticmethod
    def import_from_github(github_url, current_user):

        url = github_url.strip()

        # Caso 1: URL termina en .zip
        if url.endswith(".zip"):
            zip_url = url

        # Caso 2: URL GITHUB NORMAL
        elif "github.com" in url:

            parts = url.rstrip("/").split("/")

            if len(parts) < 5:
                return {"error": "Invalid GitHub repository URL."}

            user = parts[3]
            repo = parts[4]

            # CASO: https://github.com/user/repo/tree/branch
            if "tree" in parts:
                branch = parts[parts.index("tree") + 1]
            else:
                # Detectar rama por defecto correctamente
                branch = ModelImportService._get_default_branch(user, repo)

            zip_url = f"https://github.com/{user}/{repo}/archive/refs/heads/{branch}.zip"

        else:
            return {"error": "Invalid GitHub URL format."}

        logger.info(f"[IMPORT] Downloading GitHub ZIP: {zip_url}")

        # Descargar ZIP desde GitHub
        try:
            r = requests.get(zip_url, timeout=10)
            if r.status_code != 200:
                return {"error": f"GitHub download failed: HTTP {r.status_code}"}
        except Exception as e:
            return {"error": f"Error downloading from GitHub: {e}"}

        # Preparar carpeta temporal
        base_temp = current_user.temp_folder()
        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)
        os.makedirs(base_temp, exist_ok=True)

        zip_path = os.path.join(base_temp, "repo.zip")
        with open(zip_path, "wb") as f:
            f.write(r.content)

        extract_path = os.path.join(base_temp, "imported")
        os.makedirs(extract_path, exist_ok=True)

        # Extraer ZIP
        try:
            with zipfile.ZipFile(zip_path, "r") as z:
                for member in z.namelist():
                    member_path = os.path.join(extract_path, member)
                    if not ModelImportService._is_safe_path(extract_path, member_path):
                        return {"error": f"Unsafe ZIP entry: {member}"}
                z.extractall(extract_path)

        except Exception as e:
            return {"error": f"Error extracting GitHub ZIP: {e}"}

        if not os.listdir(extract_path):
            return {"error": "GitHub ZIP extracted but contained no files."}

        logger.info(f"[IMPORT] GitHub ZIP extracted successfully at: {extract_path}")

        return {"path": extract_path, "source": "github"}
