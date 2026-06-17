"""Module execution entrypoint for `python -m ecomextract`."""

from __future__ import annotations

import sys

from .cli import main


def run() -> None:
    raise SystemExit(main())


if __name__ == "__main__":
    run()