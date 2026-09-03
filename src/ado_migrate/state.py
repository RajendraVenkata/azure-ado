import json
import os
from typing import Optional


class StateStore:
    def __init__(self, path: str):
        self._path = path
        self._items: dict[str, dict[str, dict]] = {}
        self._failures: dict[str, list[str]] = {}

    def load(self) -> None:
        if not os.path.exists(self._path):
            self._items = {}
            self._failures = {}
            return

        with open(self._path) as f:
            data = json.load(f)
        self._items = data.get("items", {})
        self._failures = data.get("failures", {})

    def save(self) -> None:
        with open(self._path, "w") as f:
            json.dump(
                {"items": self._items, "failures": self._failures},
                f,
                indent=2,
                sort_keys=True,
            )

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

    def list_destination_ids(self, artifact_type: str) -> dict[str, str]:
        return {
            source_id: entry["destination_id"]
            for source_id, entry in self._items.get(artifact_type, {}).items()
        }

    def record_failure(self, artifact_type: str, error: str) -> None:
        self._failures.setdefault(artifact_type, []).append(error)

    def get_failures(self, artifact_type: str) -> list[str]:
        return list(self._failures.get(artifact_type, []))
