"""Helpers for normalizing scraped text into typed values."""

from __future__ import annotations

import re

PRICE_PATTERN = re.compile(r"(?P<value>\d{1,3}(?:,\d{3})*(?:\.\d{2})?|\d+(?:\.\d{2})?)")
IN_STOCK_MARKERS = ("in stock", "available", "ships now", "ready to ship")
OUT_OF_STOCK_MARKERS = ("out of stock", "sold out", "unavailable", "currently unavailable", "product is not available at the moment")


def normalize_whitespace(text: str) -> str:
    # O(n) pass over the input text length.
    return re.sub(r"\s+", " ", text.strip())


def parse_price_text(text: str) -> float:
    # O(n) scan across the candidate price text.
    normalized_text = normalize_whitespace(text).replace("$", "").replace("€", "").replace("USD", "").replace("EUR", "")
    match = PRICE_PATTERN.search(normalized_text)
    if match is None:
        raise ValueError(f"Could not parse a numeric price from: {text!r}")

    return float(match.group("value").replace(",", ""))


def parse_stock_status_text(text: str) -> tuple[bool, str]:
    # O(n) scan across a single normalized status string.
    normalized_text = normalize_whitespace(text)
    lowered_text = normalized_text.casefold()

    if any(marker in lowered_text for marker in OUT_OF_STOCK_MARKERS):
        return False, "Out of stock"

    if any(marker in lowered_text for marker in IN_STOCK_MARKERS):
        return True, "In stock"

    raise ValueError(f"Could not determine stock status from: {text!r}")
