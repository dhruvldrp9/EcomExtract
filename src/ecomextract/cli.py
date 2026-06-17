"""Command-line entrypoint for validating and emitting payloads."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable

from .models import CompetitorIntelligencePayload
from .storage import DEFAULT_STORAGE_PATH, LocalPayloadStore, StorageError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a competitor payload JSON document.")
    parser.add_argument(
        "--input",
        type=Path,
        help="Path to a JSON file. If omitted, payload JSON is read from standard input.",
    )
    parser.add_argument(
        "--store-dir",
        type=Path,
        default=DEFAULT_STORAGE_PATH.parent,
        help="Directory where validated payloads are appended as JSONL.",
    )
    return parser


def load_payload_text(input_path: Path | None, stdin_text: str) -> str:
    if input_path is None:
        return stdin_text

    return input_path.read_text(encoding="utf-8")


def render_payload(payload: CompetitorIntelligencePayload) -> str:
    return payload.model_dump_json(indent=2)


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(list(argv) if argv is not None else None)

    try:
        stdin_text = sys.stdin.read() if arguments.input is None else ""
        payload_text = load_payload_text(arguments.input, stdin_text)
        payload = CompetitorIntelligencePayload.model_validate_json(payload_text)
    except FileNotFoundError as error:
        print(f"Input file not found: {error.filename}", file=sys.stderr)
        return 1
    except (json.JSONDecodeError, ValueError) as error:
        print(f"Invalid payload JSON: {error}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Payload validation failed: {error}", file=sys.stderr)
        return 1

    try:
        LocalPayloadStore(arguments.store_dir / DEFAULT_STORAGE_PATH.name).append(payload)
    except StorageError as error:
        print(f"Payload storage failed: {error}", file=sys.stderr)
        return 1

    print(render_payload(payload))
    return 0