import os
import zipfile
import tempfile
import shutil
import logging

logger = logging.getLogger(__name__)


class ModelImportService:

    @staticmethod
    def _is_safe_path(base_path, target_path):
        """
        Prevent ZIP Slip attacks.
        Ensures extracted file stays inside the target directory.
        """
        return os.path.realpath(target_path).startswith(os.path.realpath(base_path))

    @staticmethod
    def import_from_zip(zip_file, current_user):
        """
        Import a dataset from a ZIP file safely.
        - Creates a clean temp folder for the user.
        - Extracts ZIP into /temp/imported
        - Returns { "path": EXTRACT_PATH, "source": "zip" }
        """

        # ============================================
        # 0. Validar extensión ZIP
        # ============================================
        if not zip_file.filename.lower().endswith(".zip"):
            return {"error": "Uploaded file is not a ZIP."}

        # ============================================
        # 1. Preparar carpeta temporal del usuario
        # ============================================
        base_temp = current_user.temp_folder()

        if os.path.exists(base_temp):
            shutil.rmtree(base_temp)

        os.makedirs(base_temp, exist_ok=True)

        # Ruta del ZIP subido
        zip_path = os.path.join(base_temp, zip_file.filename)

        try:
            zip_file.save(zip_path)
        except Exception as e:
            return {"error": f"Error saving ZIP file: {e}"}

        # Carpeta donde se extraerá el contenido
        extract_path = os.path.join(base_temp, "imported")
        os.makedirs(extract_path, exist_ok=True)

        # ============================================
        # 2. EXTRAER ZIP SEGURO
        # ============================================
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                
                # Comprobar que no esté vacío
                if len(zip_ref.namelist()) == 0:
                    return {"error": "ZIP is empty."}

                for member in zip_ref.namelist():
                    member_path = os.path.join(extract_path, member)

                    # PROTECCIÓN ZIP-SLIP
                    if not ModelImportService._is_safe_path(extract_path, member_path):
                        return {"error": f"Unsafe ZIP entry detected: {member}"}

                # Extraer ahora sí
                zip_ref.extractall(extract_path)

        except zipfile.BadZipFile:
            return {"error": "Invalid or corrupted ZIP file."}
        except Exception as e:
            return {"error": f"Error extracting ZIP: {e}"}

        # ============================================
        # 3. Validar contenido extraído
        # ============================================
        if not os.listdir(extract_path):
            return {"error": "ZIP extracted but contains no valid files."}

        logger.info(f"[IMPORT] ZIP extracted successfully at {extract_path}")

        # ============================================
        # 4. BORRAR ZIP SUBIDO PARA AHORRAR ESPACIO
        # ============================================
        try:
            os.remove(zip_path)
        except Exception:
            pass

        return {
            "path": extract_path,
            "source": "zip"
        }
