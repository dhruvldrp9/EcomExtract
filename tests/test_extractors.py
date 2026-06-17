from datetime import datetime, timezone

import pytest

from ecomextract.extractors import extract_coros_payload, extract_mobvoi_payload


COROS_HTML = """
<html>
  <body>
    <h1>COROS PACE 3 Base Model</h1>
    <div class="price" data-testid="price">$199.00</div>
    <div class="stock-status">In stock</div>
  </body>
</html>
""".strip()

MOBVOI_HTML = """
<html>
  <body>
    <h1>TicWatch Pro 5 Flagship Model</h1>
    <div class="price" data-price="USD 279.99">USD 279.99</div>
    <div class="stock-status">Sold out</div>
  </body>
</html>
""".strip()


def test_should_build_coros_payload_when_expected_price_and_stock_are_present():
    scraped_at = datetime(2026, 6, 16, 10, 0, tzinfo=timezone.utc)

    payload = extract_coros_payload(COROS_HTML, scraped_at=scraped_at)

    assert payload.metadata.scraped_at == scraped_at
    assert payload.product_data.competitor_id == "coros_global"
    assert payload.product_data.financials.current_price == 199.0
    assert payload.product_data.inventory.is_in_stock is True


def test_should_build_mobvoi_payload_when_expected_price_and_stock_are_present():
    payload = extract_mobvoi_payload(MOBVOI_HTML)

    assert payload.product_data.competitor_id == "mobvoi_us"
    assert payload.product_data.financials.original_msrp == 349.0
    assert payload.product_data.financials.current_price == 279.99
    assert payload.product_data.inventory.is_in_stock is False


def test_should_build_mobvoi_payload_when_product_is_unavailable():
    unavailable_html = """
    <html>
      <body>
        <h1>TicWatch Pro 5 Flagship Model</h1>
        <div>Product is not available at the moment</div>
      </body>
    </html>
    """.strip()

    payload = extract_mobvoi_payload(unavailable_html)

    assert payload.product_data.competitor_id == "mobvoi_us"
    assert payload.product_data.financials.original_msrp is None
    assert payload.product_data.financials.current_price is None
    assert payload.product_data.inventory.is_in_stock is False


def test_should_raise_value_error_when_price_is_missing():
    with pytest.raises(ValueError, match="Could not locate a price value"):
        extract_coros_payload("<html><body><div>In stock</div></body></html>")
