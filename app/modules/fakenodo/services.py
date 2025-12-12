import os
import requests
import logging
import itertools
from typing import Any, Dict

logger = logging.getLogger(__name__)


class FakenodoService:

    def __init__(self):
        self._state: Dict[str, Any] = {
            "next_id": itertools.count(1),
            "records": {},
        }

    def create_new_deposition(self, payload: dict):
        payload = payload or {}
        metadata = payload.get("metadata", {})

        record_id = next(self._state["next_id"])
        record = {"id": record_id, "metadata": metadata, "files": [], "doi": None, "published": False}
        self._state["records"][record_id] = record
        return record

    def delete_deposition(self, deposition_id):
        deposition_id_int = int(deposition_id)
        if deposition_id_int in self._state["records"]:
            del self._state["records"][deposition_id_int]
            return True
        return False

    def get_all_depositions(self):
        return {"depositions": list(self._state["records"].values())}

    def upload_file(self, deposition_id: int, filename: str):
        record = self._state["records"].get(deposition_id)
        if not record:
            return None
        record["files"].append({"filename": filename})
        return {"filename": filename, "link": f"http://fakenodo.org/files/{deposition_id}/files/{filename}"}

    def publish_deposition(self, deposition_id: int):
        record = self._state["records"].get(deposition_id)
        if not record:
            return None
        doi = f"10.5072/fakenodo.{deposition_id}"
        record["doi"] = doi
        record["published"] = True
        return {"id": deposition_id, "doi": doi}

    def get_deposition(self, deposition_id: int):
        return self._state["records"].get(deposition_id)
