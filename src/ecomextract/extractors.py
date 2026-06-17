"""Storefront extraction flows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import CompetitorIntelligencePayload, Financials, Inventory, Metadata, ProductData
from .parsing import normalize_whitespace, parse_price_text, parse_stock_status_text

COROS_PRICE_PATTERNS = (
    r'data-testid=["\']price["\'][^>]*>\s*(?P<value>[^<]+?)\s*<',
    r'data-price=["\'](?P<value>[^"\']+)["\']',
    r'(?P<value>\$\s*\d+(?:,\d{3})*(?:\.\d{2})?)',
)
MOBVOI_PRICE_PATTERNS = (
    r'data-testid=["\']price["\'][^>]*>\s*(?P<value>[^<]+?)\s*<',
    r'data-price=["\'](?P<value>[^"\']+)["\']',
    r'(?P<value>USD\s*\d+(?:,\d{3})*(?:\.\d{2})?)',
    r'(?P<value>\$\s*\d+(?:,\d{3})*(?:\.\d{2})?)',
)


@dataclass(frozen=True, slots=True)
class StorefrontSpec:
    competitor_id: str
    product_name: str
    sku: str
    original_msrp: float
    price_patterns: tuple[str, ...]


COROS_SPEC = StorefrontSpec(
    competitor_id="coros_global",
    product_name="COROS PACE 3 Base Model",
    sku="PACE3-BASE",
    original_msrp=229.0,
    price_patterns=COROS_PRICE_PATTERNS,
)
MOBVOI_SPEC = StorefrontSpec(
    competitor_id="mobvoi_us",
    product_name="TicWatch Pro 5 Flagship Model",
    sku="TW5-FLAGSHIP",
    original_msrp=349.0,
    price_patterns=MOBVOI_PRICE_PATTERNS,
)


def _extract_price_text(html_text: str, patterns: tuple[str, ...]) -> str:
    # O(n * p) over the HTML length and bounded pattern count.
    import re

    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match is not None:
            return match.group("value")

    # Fallback: attempt to extract price from JSON-LD structured data
    try:
        import json

        for script_match in re.finditer(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", html_text, flags=re.IGNORECASE | re.DOTALL):
            try:
                data = json.loads(script_match.group(1))
            except Exception:
                continue

            # JSON-LD can be a list or object
            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                # Look for offers.price or priceSpecification
                offers = item.get("offers") if isinstance(item, dict) else None
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("priceSpecification", {}).get("price")
                    if price:
                        return str(price)
    except Exception:
        pass

    # Final fallback: search for a currency-looking pattern anywhere in the HTML
    import re

    money_match = re.search(r"(\$\s?[0-9]{1,3}(?:[,0-9]*)(?:\.\d{2})?)", html_text)
    if money_match:
        return money_match.group(1)

    raise ValueError("Could not locate a price value in the storefront HTML.")


def _build_payload(html_text: str, storefront: StorefrontSpec, scraped_at: datetime | None = None) -> CompetitorIntelligencePayload:
    # O(n) over the HTML text length plus bounded extraction work.
    is_in_stock, stock_status_text = parse_stock_status_text(html_text)

    normalized_text = normalize_whitespace(html_text).casefold()
    is_unavailable_page = "product is not available at the moment" in normalized_text

    original_msrp: float | None = storefront.original_msrp
    current_price: float | None = None

    if not is_unavailable_page:
        price_text = _extract_price_text(html_text, storefront.price_patterns)
        current_price = parse_price_text(price_text)

    metadata = Metadata(scraped_at=scraped_at or datetime.now(timezone.utc))
    if is_unavailable_page:
        original_msrp = None

    financials = Financials(original_msrp=original_msrp, current_price=current_price)
    inventory = Inventory(is_in_stock=is_in_stock, stock_status_text=stock_status_text)
    product_data = ProductData(
        competitor_id=storefront.competitor_id,
        product_name=storefront.product_name,
        sku=storefront.sku,
        financials=financials,
        inventory=inventory,
    )

    return CompetitorIntelligencePayload(metadata=metadata, product_data=product_data)


def extract_coros_payload(html_text: str, scraped_at: datetime | None = None) -> CompetitorIntelligencePayload:
    return _build_payload(html_text, COROS_SPEC, scraped_at)


def extract_mobvoi_payload(html_text: str, scraped_at: datetime | None = None) -> CompetitorIntelligencePayload:
    return _build_payload(html_text, MOBVOI_SPEC, scraped_at)
