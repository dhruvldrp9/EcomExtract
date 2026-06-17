"""Local storage helpers for scraped payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .models import CompetitorIntelligencePayload

DEFAULT_STORAGE_PATH = Path("data/scraped/payloads.jsonl")


class StorageError(RuntimeError):
    """Raised when local payload persistence fails."""


@dataclass(frozen=True, slots=True)
class LocalPayloadStore:
    target_path: Path = DEFAULT_STORAGE_PATH

    def append(self, payload: CompetitorIntelligencePayload) -> Path:
        # O(1) file append with bounded serialization work per payload.
        record = {
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "payload": payload.model_dump(mode="json"),
        }

        try:
            self.target_path.parent.mkdir(parents=True, exist_ok=True)
            with self.target_path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, ensure_ascii=False))
                handle.write("\n")
        except OSError as error:
            raise StorageError(f"Failed to append payload to {self.target_path}: {error}") from error

        return self.target_path