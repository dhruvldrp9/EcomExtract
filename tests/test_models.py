from datetime import datetime, timezone

import pytest

from ecomextract import (
    CompetitorIntelligencePayload,
    Financials,
    Inventory,
    Metadata,
    ProductData,
)


def test_should_build_payload_with_schema_defaults_when_valid_input_is_provided():
    payload = CompetitorIntelligencePayload.model_validate(
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

    assert payload.metadata.scraper_version == "1.0.0"
    assert payload.product_data.financials.currency == "USD"
    assert payload.product_data.inventory.is_in_stock is True
    assert payload.product_data.sku == "PACE3-BASE"


def test_should_accept_explicit_eur_currency_when_financials_are_valid():
    financials = Financials.model_validate(
        {"currency": "EUR", "original_msrp": 249.99, "current_price": 199.99}
    )

    assert financials.currency == "EUR"
    assert financials.current_price == 199.99


def test_should_accept_missing_prices_when_financials_are_unavailable():
    financials = Financials.model_validate({"original_msrp": None, "current_price": None})

    assert financials.original_msrp is None
    assert financials.current_price is None


def test_should_preserve_nested_timestamp_when_timezone_is_present():
    metadata = Metadata.model_validate({"scraped_at": datetime(2026, 6, 16, 6, 0, tzinfo=timezone.utc)})

    assert metadata.scraped_at.tzinfo is timezone.utc


def test_should_reject_unexpected_fields_when_payload_is_over_extended():
    with pytest.raises(Exception):
        CompetitorIntelligencePayload.model_validate(
            {
                "metadata": {"scraped_at": "2026-06-16T10:00:00Z", "unexpected": True},
                "product_data": {
                    "competitor_id": "mobvoi_us",
                    "product_name": "TicWatch Pro 5",
                    "sku": "TW5-FLAGSHIP",
                    "financials": {"original_msrp": 349.0, "current_price": 279.0},
                    "inventory": {"is_in_stock": False, "stock_status_text": "Out of stock"},
                },
            }
        )


def test_should_reject_negative_prices_when_financials_are_invalid():
    with pytest.raises(Exception):
        Financials.model_validate({"original_msrp": -1, "current_price": 10})


def test_should_reject_unknown_competitor_when_product_data_is_invalid():
    with pytest.raises(Exception):
        ProductData.model_validate(
            {
                "competitor_id": "unknown",
                "product_name": "Test Product",
                "sku": "TEST-001",
                "financials": {"original_msrp": 100, "current_price": 80},
                "inventory": {"is_in_stock": True, "stock_status_text": "In stock"},
            }
        )