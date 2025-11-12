# app/modules/dataset/base.py
from __future__ import annotations
from typing import Dict, Any, List

class BaseDataset:
    """
    Mixin para lógica/validaciones comunes de datasets.
    DataSet debe heredar de este mixin + db.Model.
    """

    # --- Validaciones comunes, ejecutables antes de publicar/sincronizar ---
    def validate_basic_metadata(self) -> List[str]:
        """
        Devuelve lista de errores (vacía si todo OK).
        Valida metadatos básicos existentes en self.ds_meta_data (title, authors, etc.).
        """
        errors: List[str] = []
        md = getattr(self, "ds_meta_data", None)
        if md is None:
            errors.append("Missing ds_meta_data.")
            return errors

        if not md.title or not md.title.strip():
            errors.append("Title is required.")

        # Valida autores mínimos
        if not getattr(md, "authors", []):
            errors.append("At least one author is required.")

        # Valida DOI de publicación si viene
        pub_doi = getattr(md, "publication_doi", None)
        if pub_doi and not str(pub_doi).startswith("http"):
            errors.append("publication_doi must be a URL.")
        return errors

    # --- Puntos de extensión por tipo (cada módulo puede sobreescribir estos hooks en sus modelos/servicios) ---
    def pre_publish_hook(self) -> None:
        """Hook de pre-publicación, específico por tipo (opcional)."""
        return None

    def post_publish_hook(self) -> None:
        """Hook de post-publicación, específico por tipo (opcional)."""
        return None

    # --- Utilidades compartidas (se importan lazy para evitar dependencias circulares) ---
    def get_uvlhub_doi(self) -> str:
        from app.modules.dataset.services import DataSetService
        return DataSetService().get_uvlhub_doi(self)

    def get_file_total_size_for_human(self) -> str:
        from app.modules.dataset.services import SizeService
        return SizeService().get_human_readable_size(self.get_file_total_size())

    # Nota: mantenemos to_dict() en DataSet original para no romper UI/REST existentes.
