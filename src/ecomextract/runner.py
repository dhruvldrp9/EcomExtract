"""Compatibility runner for live scraping with optional debug output."""

from __future__ import annotations

import argparse
from typing import Iterable

from .scraper import TARGETS, run_targets
from .storage import DEFAULT_STORAGE_PATH

DEFAULT_TARGET_NAMES = tuple(target.name for target in TARGETS)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the live storefront scraper.")
    parser.add_argument("--debug", action="store_true", help="Print live fetch/render/store steps.")
    parser.add_argument("--all", action="store_true", help="Discover and scrape all product pages from both platforms.")
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        help="Number of worker processes to use for scraping. Defaults to 1, or 4 in --all mode.",
    )
    parser.add_argument(
        "--target",
        action="append",
        choices=DEFAULT_TARGET_NAMES,
        help="Scrape one of the hardcoded targets. Repeat to select multiple targets.",
    )

    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.all and args.target:
        parser.error("--all cannot be combined with --target")

    workers = args.workers if args.workers is not None else (4 if args.all else 1)
    if workers < 1:
        parser.error("--workers must be at least 1")

    try:
        results = run_targets(
            DEFAULT_STORAGE_PATH,
            debug=args.debug,
            all_products=args.all,
            target_names=args.target,
            workers=workers,
        )
    except ValueError as error:
        print(f"runner error: {error}")
        return 2

    for competitor_id, info in results.items():
        print(f"{competitor_id}: {info['status']} - {info['reason']}")

    return 0 if all(info["status"] == "ok" for info in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
