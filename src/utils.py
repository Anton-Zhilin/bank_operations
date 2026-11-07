# src/utils.py
"""Вспомогательные функции"""

from datetime import datetime
from typing import Union


def parse_date(date_string: str) -> datetime:
    """Распарсить дату из строки"""
    # Пробуем разные форматы
    formats = ["%d.%m.%Y %H:%M:%S", "%d.%m.%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"]

    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unable to parse date: {date_string}")


def format_currency(amount: float, currency: str = "RUB") -> str:
    """Отформатировать сумму для отображения"""
    return f"{amount:,.2f} {currency}"


def round_to_cents(amount: float) -> float:
    """Округлить сумму до копеек"""
    return round(amount, 2)
