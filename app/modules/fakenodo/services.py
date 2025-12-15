import os
import requests
import logging
import itertools
from typing import Any, Dict, Optional
from core.configuration.configuration import uploads_folder_name

logger = logging.getLogger(__name__)


class FakenodoService:

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url
        if not self.base_url:
            self._state: Dict[str, Any] = {
                "next_id": itertools.count(1),
                "records": {},
            }

    def _is_remote(self) -> bool:
        return bool(self.base_url)

    def _dataset_to_payload(self, dataset) -> Dict:

        md = dataset.ds_meta_data
        publication_type = getattr(md.publication_type, "value", "none")
        metadata = {
            "title": md.title,
            "upload_type": "dataset" if publication_type == "none" else "publication",
            "publication_type": publication_type if publication_type != "none" else None,
            "description": md.description,
            "creators": [
                {
                    "name": author.name,
                    **({"affiliation": author.affiliation} if getattr(author, "affiliation", None) else {}),
                    **({"orcid": author.orcid} if getattr(author, "orcid", None) else {}),
                }
                for author in md.authors
            ],
            "keywords": (["astronomiahub"] if not md.tags else md.tags.split(", ") + ["astronomiahub"]),
            "access_right": "open",
            "license": "CC-BY-4.0",
        }
        return {"metadata": metadata}

    # Create 
    def create_new_deposition(self, dataset_or_payload):
        if self._is_remote():
            # remote
            if not isinstance(dataset_or_payload, dict):
                payload = self._dataset_to_payload(dataset_or_payload)
            else:
                payload = dataset_or_payload
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            return response.json()

        # Local behaviour 
        if isinstance(dataset_or_payload, dict):
            payload = dataset_or_payload or {}
            metadata = payload.get("metadata", {})
        else:
            payload = self._dataset_to_payload(dataset_or_payload)
            metadata = payload.get("metadata", {})

        record_id = next(self._state["next_id"])
        record = {"id": record_id, "metadata": metadata, "files": [], "doi": None, "published": False}
        self._state["records"][record_id] = record
        return record

    # Delete
    def delete_deposition(self, deposition_id):
        if self._is_remote():
            url = f"{self.base_url}/{deposition_id}"
            try:
                r = requests.delete(url)
                return r.status_code in (200, 204)
            except Exception:
                return False

        deposition_id_int = int(deposition_id)
        if deposition_id_int in self._state["records"]:
            del self._state["records"][deposition_id_int]
            return True
        return False
    
    # List all
    def get_all_depositions(self):
        if self._is_remote():
            r = requests.get(self.base_url)
            r.raise_for_status()
            return r.json()
        return {"depositions": list(self._state["records"].values())}
    
    # Upload file 
    def upload_file(self, dataset, deposition_id: int, hubfile, user=None):
        """
        Si remote: envía multipart a {base_url}/{deposition_id}/files (campos: file, filename)
        Si local: añade filename al registro y devuelve la estructura {filename, link}
        """
        if self._is_remote():
            url = f"{self.base_url}/{deposition_id}/files"
            filename = hubfile.name
            user_id = user.id if user is not None else getattr(dataset, "user_id", None) or ""
            file_path = os.path.join(
                uploads_folder_name(),
                f"user_{user_id}",
                f"dataset_{getattr(dataset, 'id', '')}",
                filename,
            )
            files = None
            data = {"filename": filename}
            try:
                if file_path and os.path.exists(file_path):
                    files = {"file": open(file_path, "rb")}
                    r = requests.post(url, files=files, data=data)
                    files["file"].close()
                else:
                    r = requests.post(url, data=data)
                r.raise_for_status()
                return r.json()
            except Exception as e:
                logger.exception("Failed to upload file to remote fakenodo: %s", e)
                raise

        # Local: append filename
        record = self._state["records"].get(deposition_id)
        if not record:
            return None
        filename = hubfile.name
        record["files"].append({"filename": filename})
        return {"filename": filename, "link": f"http://fakenodo.org/files/{deposition_id}/files/{filename}"}


    # Publish
    def publish_deposition(self, deposition_id: int):
        if self._is_remote():
            url = f"{self.base_url}/{deposition_id}/actions/publish"
            r = requests.post(url)
            r.raise_for_status()
            return r.json()

        record = self._state["records"].get(deposition_id)
        if not record:
            return None
        doi = f"10.5072/fakenodo.{deposition_id}"
        record["doi"] = doi
        record["published"] = True
        return {"id": deposition_id, "doi": doi}
    

    # Get single deposition
    def get_deposition(self, deposition_id: int):
        if self._is_remote():
            url = f"{self.base_url}/{deposition_id}"
            r = requests.get(url)
            r.raise_for_status()
            return r.json()
        return self._state["records"].get(deposition_id)
    
    #Get doi
    def get_doi(self, deposition_id: int) -> Optional[str]:
        record = self.get_deposition(deposition_id)
        if record and record.get("published"):
            return record.get("doi")
        return None