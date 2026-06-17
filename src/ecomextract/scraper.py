"""Live scraping helpers with sitemap-driven product discovery.

The runner supports two modes:
- hardcoded targets for the known storefront pages
- sitemap-driven discovery for product pages on both platforms

When `workers` is greater than 1, target scraping runs in parallel using a
process pool. The main process still performs storage so JSONL writes remain
serialized and predictable.
"""
from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
import re
import time

import requests

from .extractors import extract_coros_payload, extract_mobvoi_payload
from .models import CompetitorIntelligencePayload, Financials, Inventory, Metadata, ProductData
from .parsing import normalize_whitespace, parse_price_text, parse_stock_status_text
from .storage import LocalPayloadStore


COROS_SITEMAP_URL = "https://coros.com/sitemap.xml"
MOBVOI_SITEMAP_URL = "https://www.mobvoi.com/sitemap.xml"
SITEMAP_NAMESPACE = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
UNAVAILABLE_PAGE_MARKER = "product is not available at the moment"

GENERIC_PRICE_PATTERNS = (
    r'data-testid=["\']price["\'][^>]*>\s*(?P<value>[^<]+?)\s*<',
    r'data-price=["\'](?P<value>[^"\']+)["\']',
    r'priceRange"[^\n]*?"minVariantPrice":\{"amount":"(?P<value>[^"]+)"',
    r'"price":"(?P<value>[^"]+)"',
    r'(?P<value>USD\s*\d+(?:,\d{3})*(?:\.\d{2})?)',
    r'(?P<value>\$\s*\d+(?:,\d{3})*(?:\.\d{2})?)',
)


@dataclass(frozen=True, slots=True)
class Target:
    name: str
    url: str
    platform_id: str
    use_playwright_first: bool = False
    is_discovered: bool = False


TARGETS = [
    Target(name="coros_global", url="https://coros.com/pace3", platform_id="coros_global"),
    Target(
        name="mobvoi_us",
        url="https://www.mobvoi.com/us/products/ticwatchpro5",
        platform_id="mobvoi_us",
        use_playwright_first=True,
    ),
]

PLATFORM_EXTRACTORS: dict[str, Callable[[str, datetime | None], CompetitorIntelligencePayload]] = {
    "coros_global": extract_coros_payload,
    "mobvoi_us": extract_mobvoi_payload,
}


def fetch_html_requests(url: str, timeout: int = 15) -> str:
    headers = {"User-Agent": "EcomExtractBot/1.0 (+https://example.com)"}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def render_with_playwright(url: str, timeout: int = 30) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as exc:  # ImportError or Playwright not configured
        raise RuntimeError(
            "Playwright is not available. Install it with: \n"
            "  python -m pip install playwright\n"
            "then install browsers: \n"
            "  playwright install\n"
            "After that re-run the scraper."
        ) from exc

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle", timeout=timeout * 1000)
        time.sleep(0.5)
        html = page.content()
        browser.close()
        return html


def _is_coros_product_url(url: str) -> bool:
    parsed_url = urlparse(url)
    if parsed_url.netloc != "coros.com":
        return False

    path = parsed_url.path.strip("/")
    if not path or "/" in path or ":" in path:
        return False

    excluded_tokens = {
        "buy",
        "teaser",
        "products",
        "privacy",
        "login",
        "support",
        "blog",
        "news",
        "contact",
        "faq",
        "events",
        "declaration-of-conformity",
        "forgetpassword",
    }
    return path not in excluded_tokens


def _is_mobvoi_product_url(url: str) -> bool:
    parsed_url = urlparse(url)
    if parsed_url.netloc not in {"mobvoi.com", "www.mobvoi.com"}:
        return False

    path = parsed_url.path.rstrip("/")
    return path.startswith("/products/") or path.startswith("/us/products/")


def _extract_first_text(pattern: str, html_text: str) -> str | None:
    match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
    if match is None:
        return None

    return normalize_whitespace(re.sub(r"<[^>]+>", " ", match.group("value")))


def _extract_product_name(html_text: str, url: str) -> str:
    name = _extract_first_text(r"<h1[^>]*>(?P<value>.*?)</h1>", html_text)
    if name:
        return name

    title = _extract_first_text(r"<title[^>]*>(?P<value>.*?)</title>", html_text)
    if title:
        for separator in (" | ", " - ", " – "):
            if separator in title:
                title = title.split(separator, 1)[0]
                break
        return normalize_whitespace(title)

    slug = Path(urlparse(url).path.rstrip("/")).name
    if slug:
        return slug.replace("-", " ").strip().title()

    raise ValueError(f"Could not determine a product name for {url!r}")


def _extract_sku(url: str) -> str:
    slug = Path(urlparse(url).path.rstrip("/")).name
    if slug:
        return slug.replace("/", "-").replace("_", "-").upper()

    return urlparse(url).netloc.upper()


def _extract_price_text(html_text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, html_text, flags=re.IGNORECASE | re.DOTALL)
        if match is not None:
            return match.group("value")

    try:
        import json

        for script_match in re.finditer(
            r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        ):
            try:
                data = json.loads(script_match.group(1))
            except Exception:
                continue

            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                offers = item.get("offers") if isinstance(item, dict) else None
                if isinstance(offers, dict):
                    price = offers.get("price") or offers.get("priceSpecification", {}).get("price")
                    if price:
                        return str(price)
    except Exception:
        pass

    raise ValueError("Could not locate a price value in the storefront HTML.")


def _build_generic_payload(
    html_text: str,
    url: str,
    platform_id: str,
    scraped_at: datetime | None = None,
) -> CompetitorIntelligencePayload:
    normalized_text = normalize_whitespace(html_text).casefold()
    product_name = _extract_product_name(html_text, url)
    is_in_stock, stock_status_text = parse_stock_status_text(html_text)

    current_price = None
    if UNAVAILABLE_PAGE_MARKER not in normalized_text:
        try:
            price_text = _extract_price_text(html_text, GENERIC_PRICE_PATTERNS)
            current_price = parse_price_text(price_text)
        except ValueError:
            current_price = None

    metadata = Metadata(scraped_at=scraped_at or datetime.now(timezone.utc))
    financials = Financials(original_msrp=None, current_price=current_price)
    inventory = Inventory(is_in_stock=is_in_stock, stock_status_text=stock_status_text)
    product_data = ProductData(
        competitor_id=platform_id,
        product_name=product_name,
        sku=_extract_sku(url),
        financials=financials,
        inventory=inventory,
    )

    return CompetitorIntelligencePayload(metadata=metadata, product_data=product_data)


def discover_product_urls_from_sitemap(sitemap_url: str, predicate: Callable[[str], bool]) -> list[str]:
    sitemap_xml = fetch_html_requests(sitemap_url)
    try:
        root = ET.fromstring(sitemap_xml)
    except ET.ParseError as error:
        raise RuntimeError(f"Failed to parse sitemap {sitemap_url}: {error}") from error

    discovered_urls: list[str] = []
    for loc in root.findall(f".//{SITEMAP_NAMESPACE}loc"):
        if loc.text is None:
            continue

        candidate_url = loc.text.strip()
        if candidate_url and predicate(candidate_url):
            discovered_urls.append(candidate_url)

    return sorted(set(discovered_urls))


def _build_discovered_target(platform_id: str, url: str, use_playwright_first: bool) -> Target:
    slug = Path(urlparse(url).path.rstrip("/")).name or "index"
    return Target(
        name=f"{platform_id}:{slug}",
        url=url,
        platform_id=platform_id,
        use_playwright_first=use_playwright_first,
        is_discovered=True,
    )


def discover_all_targets() -> list[Target]:
    discovered_targets: list[Target] = []

    for product_url in discover_product_urls_from_sitemap(COROS_SITEMAP_URL, _is_coros_product_url):
        discovered_targets.append(_build_discovered_target("coros_global", product_url, False))

    for product_url in discover_product_urls_from_sitemap(MOBVOI_SITEMAP_URL, _is_mobvoi_product_url):
        discovered_targets.append(_build_discovered_target("mobvoi_us", product_url, True))

    return discovered_targets


def resolve_targets(target_names: Iterable[str] | None = None, all_products: bool = False) -> list[Target]:
    if all_products:
        return discover_all_targets()

    if target_names is None:
        return list(TARGETS)

    target_lookup = {target.name: target for target in TARGETS}
    selected_targets: list[Target] = []
    for target_name in target_names:
        try:
            selected_targets.append(target_lookup[target_name])
        except KeyError as error:
            raise ValueError(f"Unknown target: {target_name}") from error

    return selected_targets


def _looks_like_product_page(target: Target, html_text: str) -> bool:
    normalized_text = normalize_whitespace(html_text).casefold()

    if target.platform_id == "coros_global":
        return "pricerange" in normalized_text and "minvariantprice" in normalized_text

    if target.platform_id == "mobvoi_us":
        return (
            "/products/" in target.url
            and (
                UNAVAILABLE_PAGE_MARKER in normalized_text
                or "buy now" in normalized_text
                or "ticwatch" in normalized_text
            )
        )

    return False


def _scrape_target_job(target: Target, debug: bool = False) -> dict:
    logs: list[str] = []

    try:
        if debug:
            logs.append(f"[fetch] {target.name} -> {target.url}")

        if target.use_playwright_first:
            try:
                html_text = render_with_playwright(target.url)
                if debug:
                    logs.append(f"[render] {target.name} -> playwright")
            except Exception:
                html_text = fetch_html_requests(target.url)
                if debug:
                    logs.append(f"[render] {target.name} -> requests fallback")
        else:
            html_text = fetch_html_requests(target.url)
            if debug:
                logs.append(f"[render] {target.name} -> requests")

        if target.is_discovered and not _looks_like_product_page(target, html_text):
            if debug:
                logs.append(f"[skip] {target.name} -> non-product page")
            return {
                "name": target.name,
                "status": "skipped",
                "reason": "non-product page",
                "logs": logs,
            }

        if target.is_discovered:
            payload = _build_generic_payload(html_text, target.url, target.platform_id)
        else:
            extractor = PLATFORM_EXTRACTORS[target.platform_id]
            payload = extractor(html_text, scraped_at=datetime.now(timezone.utc))

        if debug:
            logs.append(f"[extract] {target.name} -> ok")

        return {
            "name": target.name,
            "status": "ok",
            "reason": "ok",
            "payload": payload.model_dump(mode="json"),
            "logs": logs,
        }
    except Exception as error:
        if debug:
            logs.append(f"[error] {target.name} -> {error}")

        return {
            "name": target.name,
            "status": "fail",
            "reason": str(error),
            "logs": logs,
        }


def _store_result(store: LocalPayloadStore, result: dict, debug: bool) -> dict:
    for log_line in result.get("logs", []):
        if debug:
            print(log_line)

    if result["status"] == "skipped":
        return {"status": "skipped", "reason": result["reason"]}

    if result["status"] != "ok":
        return {"status": "fail", "reason": result["reason"]}

    payload = CompetitorIntelligencePayload.model_validate(result["payload"])
    stored_path = store.append(payload)
    if debug:
        print(f"[store] {result['name']} -> {stored_path}")

    return {"status": "ok", "reason": "ok"}


def run_targets(
    store_path: str | Path,
    debug: bool = False,
    all_products: bool = False,
    target_names: Iterable[str] | None = None,
    workers: int = 1,
) -> dict[str, dict[str, str]]:
    """Fetch targets, extract payloads, and append validated records to storage."""

    results: dict[str, dict[str, str]] = {}
    store = LocalPayloadStore(Path(store_path))
    targets = resolve_targets(target_names=target_names, all_products=all_products)

    if debug:
        mode = "all" if all_products else ("selected" if target_names is not None else "default")
        print(f"[mode] {mode} -> {len(targets)} targets")

    if workers > 1 and len(targets) > 1:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_scrape_target_job, target, debug) for target in targets]
            for future in as_completed(futures):
                result = future.result()
                results[result["name"]] = _store_result(store, result, debug)
    else:
        for target in targets:
            result = _scrape_target_job(target, debug)
            results[result["name"]] = _store_result(store, result, debug)

    return results