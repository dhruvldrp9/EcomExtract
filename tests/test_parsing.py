import pytest

from ecomextract.browser import BrowserProfile
from ecomextract.parsing import parse_price_text, parse_stock_status_text


def test_should_parse_price_text_when_currency_symbol_is_present():
    assert parse_price_text("$1,299.99") == 1299.99


def test_should_parse_price_text_when_currency_code_is_present():
    assert parse_price_text("USD 249.00") == 249.0


def test_should_raise_value_error_when_price_text_has_no_numeric_value():
    with pytest.raises(ValueError, match="Could not parse a numeric price"):
        parse_price_text("not a price")


def test_should_normalize_in_stock_status_when_stock_text_indicates_availability():
    is_in_stock, stock_status_text = parse_stock_status_text("Ships now, in stock")

    assert is_in_stock is True
    assert stock_status_text == "In stock"


def test_should_normalize_out_of_stock_status_when_stock_text_indicates_unavailable():
    is_in_stock, stock_status_text = parse_stock_status_text("Currently unavailable - sold out")

    assert is_in_stock is False
    assert stock_status_text == "Out of stock"


def test_should_raise_value_error_when_stock_status_is_ambiguous():
    with pytest.raises(ValueError, match="Could not determine stock status"):
        parse_stock_status_text("check back later")


def test_should_choose_user_agent_deterministically_when_index_is_provided():
    profile = BrowserProfile()

    assert profile.choose_user_agent(index=1) == profile.user_agents[1]


def test_should_sample_interaction_delay_when_random_source_is_provided():
    class FakeRandom:
        def uniform(self, lower_bound: float, upper_bound: float) -> float:
            return (lower_bound + upper_bound) / 2

    profile = BrowserProfile()

    assert profile.sample_interaction_delay(random_source=FakeRandom()) == 3.5
