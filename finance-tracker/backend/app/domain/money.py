"""Работа с денежными суммами.

Все вычисления ведутся в Decimal с округлением до копейки.
В базе суммы хранятся целыми числами (копейки), чтобы не терять точность.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

CENTS = Decimal("0.01")
CURRENCY_TOKENS = ("\u20bd", "руб.", "руб", "р.")


def to_decimal(value) -> Decimal:
    """Приводит число или строку к Decimal с двумя знаками после запятой."""
    if isinstance(value, Decimal):
        result = value
    elif isinstance(value, bool):
        raise TypeError("логическое значение нельзя использовать как сумму")
    elif isinstance(value, (int, str)):
        text = str(value).strip().replace("\u00a0", "").replace(" ", "")
        text = text.replace(",", ".")
        try:
            result = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"не удалось разобрать сумму: {value!r}") from exc
    elif isinstance(value, float):
        result = Decimal(repr(value))
    else:
        raise TypeError(
            f"сумма должна быть числом или строкой, получено {type(value).__name__}"
        )
    if not result.is_finite():
        raise ValueError("сумма должна быть конечным числом")
    return result.quantize(CENTS, rounding=ROUND_HALF_UP)


def to_cents(value) -> int:
    """Переводит сумму в целые копейки для хранения в базе."""
    return int(to_decimal(value) * 100)


def from_cents(cents: int) -> Decimal:
    """Переводит копейки обратно в Decimal с двумя знаками."""
    return (Decimal(int(cents)) / 100).quantize(CENTS)


def format_money(value) -> str:
    """Форматирует сумму в вид «1 234,50 \u20bd» с разделителем тысяч."""
    amount = to_decimal(value)
    sign = "-" if amount < 0 else ""
    whole, fraction = f"{abs(amount):.2f}".split(".")
    groups: list[str] = []
    while len(whole) > 3:
        groups.insert(0, whole[-3:])
        whole = whole[:-3]
    groups.insert(0, whole)
    return f"{sign}{' '.join(groups)},{fraction} \u20bd"


def parse_money(text: str) -> Decimal:
    """Разбирает строку вида «1 234,50 \u20bd» в Decimal."""
    if not isinstance(text, str):
        raise TypeError("на вход парсера ожидается строка")
    cleaned = text.strip()
    for token in CURRENCY_TOKENS:
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    if cleaned in {"", "-", "+", "."}:
        raise ValueError(f"не удалось разобрать сумму: {text!r}")
    return to_decimal(cleaned)


def percent(part, total) -> float:
    """Возвращает долю part от total в процентах, округлённую до 0,1."""
    part_d = to_decimal(part)
    total_d = to_decimal(total)
    if total_d == 0:
        return 0.0
    return round(float(part_d / total_d * 100), 1)
