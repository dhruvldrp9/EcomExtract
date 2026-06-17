from io import StringIO
from pathlib import Path

from ecomextract import CompetitorIntelligencePayload
from ecomextract.cli import main, render_payload


VALID_PAYLOAD = """
{
  "metadata": {"scraped_at": "2026-06-16T10:00:00Z"},
  "product_data": {
    "competitor_id": "coros_global",
    "product_name": "COROS PACE 3 Base Model",
    "sku": "PACE3-BASE",
    "financials": {"original_msrp": 229.0, "current_price": 199.0},
    "inventory": {"is_in_stock": true, "stock_status_text": "In stock"}
  }
}
""".strip()


def test_should_render_normalized_json_when_payload_is_valid():
    payload = CompetitorIntelligencePayload.model_validate_json(VALID_PAYLOAD)

    rendered = render_payload(payload)

    assert '"competitor_id": "coros_global"' in rendered
    assert '"current_price": 199.0' in rendered


def test_should_return_zero_when_valid_payload_is_read_from_stdin(monkeypatch, capsys, tmp_path: Path):
    monkeypatch.setattr("sys.stdin", StringIO(VALID_PAYLOAD))

    store_dir = tmp_path / "scraped"
    exit_code = main(["--store-dir", str(store_dir)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"product_name": "COROS PACE 3 Base Model"' in captured.out
    assert (store_dir / "payloads.jsonl").exists()


def test_should_return_zero_when_valid_payload_is_read_from_file(tmp_path: Path, capsys):
    payload_file = tmp_path / "payload.json"
    payload_file.write_text(VALID_PAYLOAD, encoding="utf-8")

    store_dir = tmp_path / "storage"
    exit_code = main(["--input", str(payload_file), "--store-dir", str(store_dir)])

    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"sku": "PACE3-BASE"' in captured.out
    assert (store_dir / "payloads.jsonl").exists()


def test_should_return_non_zero_when_payload_json_is_invalid(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", StringIO("{"))

    exit_code = main(["--store-dir", "ignored"])

    captured = capsys.readouterr()

    assert exit_code == 1
    assert "Invalid payload JSON" in captured.err