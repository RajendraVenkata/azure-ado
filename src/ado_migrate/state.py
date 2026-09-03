import json
import os
from typing import Optional


class StateStore:
    def __init__(self, path: str):
        self._path = path
        self._items: dict[str, dict[str, dict]] = {}

    def load(self) -> None:
        if not os.path.exists(self._path):
            self._items = {}
            return

        with open(self._path) as f:
            self._items = json.load(f)

    def save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(self._items, f, indent=2, sort_keys=True)

    def mark_complete(
        self, artifact_type: str, source_id: str, destination_id: str
    ) -> None:
        self._items.setdefault(artifact_type, {})[source_id] = {
            "status": "complete",
            "destination_id": destination_id,
        }

    def is_complete(self, artifact_type: str, source_id: str) -> bool:
        entry = self._items.get(artifact_type, {}).get(source_id)
        return entry is not None and entry["status"] == "complete"

    def get_destination_id(
        self, artifact_type: str, source_id: str
    ) -> Optional[str]:
        entry = self._items.get(artifact_type, {}).get(source_id)
        return entry["destination_id"] if entry else None
