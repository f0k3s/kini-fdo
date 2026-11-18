"""Юнит-тесты работы с суммами."""

from decimal import Decimal

import pytest

from app.domain.money import (
    format_money,
    from_cents,
    parse_money,
    percent,
    to_cents,
    to_decimal,
)


class TestToDecimal:
    def test_string_with_two_places(self):
        assert to_decimal("1234.50") == Decimal("1234.50")

    def test_string_with_comma(self):
        assert to_decimal("1234,5") == Decimal("1234.50")

    def test_integer_gets_two_places(self):
        assert to_decimal(100) == Decimal("100.00")

    def test_rounding_half_up(self):
        assert to_decimal("0.005") == Decimal("0.01")

    def test_rounding_down(self):
        assert to_decimal("0.004") == Decimal("0.00")

    def test_negative_keeps_sign(self):
        assert to_decimal("-10.5") == Decimal("-10.50")

    def test_bool_rejected_with_type_error(self):
        with pytest.raises(TypeError):
            to_decimal(True)

    def test_garbage_rejected_with_value_error(self):
        with pytest.raises(ValueError):
            to_decimal("не сумма")

    def test_nan_rejected(self):
        with pytest.raises(ValueError):
            to_decimal("NaN")

    def test_list_rejected_with_type_error(self):
        with pytest.raises(TypeError):
            to_decimal([1, 2])


class TestCents:
    def test_to_cents(self):
        assert to_cents("12.34") == 1234

    def test_to_cents_rounds(self):
        assert to_cents("12.345") == 1235

    def test_from_cents(self):
        assert from_cents(1234) == Decimal("12.34")

    def test_round_trip_is_lossless(self):
        for value in ["0.01", "99.99", "1000000.00", "7.10"]:
            assert from_cents(to_cents(value)) == Decimal(value)


class TestFormatMoney:
    def test_thousands_separator(self):
        assert format_money("1234.5") == "1 234,50 \u20bd"

    def test_millions(self):
        assert format_money("1234567.89") == "1 234 567,89 \u20bd"

    def test_negative(self):
        assert format_money("-1234") == "-1 234,00 \u20bd"

    def test_zero(self):
        assert format_money(0) == "0,00 \u20bd"

    def test_small_value(self):
        assert format_money("0.05") == "0,05 \u20bd"


class TestParseMoney:
    def test_with_currency_sign(self):
        assert parse_money("1 234,50 \u20bd") == Decimal("1234.50")

    def test_with_nbsp(self):
        assert parse_money("1\u00a0234,50") == Decimal("1234.50")

    def test_without_currency(self):
        assert parse_money("99.99") == Decimal("99.99")

    def test_rub_suffix(self):
        assert parse_money("500 руб.") == Decimal("500.00")

    def test_empty_rejected(self):
        with pytest.raises(ValueError):
            parse_money("   ")

    def test_dash_only_rejected(self):
        with pytest.raises(ValueError):
            parse_money("-")

    def test_non_string_rejected(self):
        with pytest.raises(TypeError):
            parse_money(1234)


class TestPercent:
    def test_simple_share(self):
        assert percent("25", "100") == 25.0

    def test_rounds_to_one_place(self):
        assert percent("1", "3") == 33.3

    def test_zero_total_gives_zero(self):
        assert percent("10", "0") == 0.0
