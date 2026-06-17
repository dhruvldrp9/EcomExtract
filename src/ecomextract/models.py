"""Pydantic models for the competitor intelligence payload."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA_VERSION = "1.0.0"


class StrictBaseModel(BaseModel):
    """Base model that rejects unexpected fields."""

    model_config = ConfigDict(extra="forbid")


class Metadata(StrictBaseModel):
    scraped_at: datetime
    scraper_version: str = SCHEMA_VERSION


class Financials(StrictBaseModel):
    currency: Literal["USD", "EUR"] = "USD"
    original_msrp: float | None = Field(None, ge=0, description="Baseline manufacturer suggested retail price")
    current_price: float | None = Field(None, ge=0, description="Active web-scraped purchase price numeric")


class Inventory(StrictBaseModel):
    is_in_stock: bool
    stock_status_text: str


class ProductData(StrictBaseModel):
    competitor_id: Literal["coros_global", "mobvoi_us"]
    product_name: str
    sku: str
    financials: Financials
    inventory: Inventory


class CompetitorIntelligencePayload(StrictBaseModel):
    metadata: Metadata
    product_data: ProductData