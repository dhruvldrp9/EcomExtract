import json
from pathlib import Path

import pytest

from ecomextract import CompetitorIntelligencePayload, LocalPayloadStore, StorageError


VALID_PAYLOAD = CompetitorIntelligencePayload.model_validate(
    {
        "metadata": {"scraped_at": "2026-06-16T10:00:00Z"},
        "product_data": {
            "competitor_id": "coros_global",
            "product_name": "COROS PACE 3 Base Model",
            "sku": "PACE3-BASE",
            "financials": {"original_msrp": 229.0, "current_price": 199.0},
            "inventory": {"is_in_stock": True, "stock_status_text": "In stock"},
        },
    }
)


def test_should_append_jsonl_record_when_payload_is_valid(tmp_path: Path):
    target_path = tmp_path / "scraped" / "payloads.jsonl"
    store = LocalPayloadStore(target_path)

    written_path = store.append(VALID_PAYLOAD)

    assert written_path == target_path
    lines = target_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["payload"]["product_data"]["competitor_id"] == "coros_global"


def test_should_create_parent_directory_when_target_path_is_nested(tmp_path: Path):
    target_path = tmp_path / "nested" / "records" / "payloads.jsonl"
    store = LocalPayloadStore(target_path)

    store.append(VALID_PAYLOAD)

    assert target_path.exists()
    assert target_path.parent.exists()


def test_should_append_multiple_records_when_store_is_used_twice(tmp_path: Path):
    target_path = tmp_path / "payloads.jsonl"
    store = LocalPayloadStore(target_path)

    store.append(VALID_PAYLOAD)
    store.append(VALID_PAYLOAD)

    assert target_path.read_text(encoding="utf-8").count("\n") == 2


def test_should_raise_storage_error_when_target_path_is_a_directory(tmp_path: Path):
    target_path = tmp_path / "payloads.jsonl"
    target_path.mkdir()
    store = LocalPayloadStore(target_path)

    with pytest.raises(StorageError, match="Failed to append payload"):
        store.append(VALID_PAYLOAD)