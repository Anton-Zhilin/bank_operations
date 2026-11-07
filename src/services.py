"""Модуль сервисов для анализа банковских транзакций."""

import json
import math
import re
from datetime import datetime
from functools import reduce
from pathlib import Path
from typing import Any, Dict, List, Union, cast

import pandas as pd

# 1. Выгодные категории повышенного кешбэка


def profitable_categories(data: Union[List[Dict[str, Any]], Any], year: int, month: int) -> str:
    """
    Анализирует, сколько кешбэка можно было бы заработать по каждой категории
    в указанном месяце года.
    """
    # Преобразуем DataFrame в список словарей (если передан DataFrame)
    transactions = data.to_dict("records") if hasattr(data, "to_dict") else list(data)

    # Фильтр: транзакции за нужный год и месяц
    def matches_period(t: Dict[str, Any]) -> bool:
        date_str = str(t.get("Дата операции", ""))
        try:
            dt = datetime.strptime(date_str.split()[0], "%d.%m.%Y")
            return dt.year == year and dt.month == month
        except (ValueError, IndexError, AttributeError):
            return False

    filtered = list(filter(matches_period, transactions))

    # Accumulator для reduce: суммируем кешбэк по категориям
    def accumulate(results: Dict[str, float], t: Dict[str, Any]) -> Dict[str, float]:
        category = str(t.get("Категория", "Неизвестно"))
        cashback_raw = t.get("Кешбэк", 0)
        try:
            cashback = float(cashback_raw) if cashback_raw is not None and str(cashback_raw) != "nan" else 0.0
        except (ValueError, TypeError):
            cashback = 0.0
        results[category] = results.get(category, 0) + cashback
        return results

    result: Dict[str, float] = reduce(accumulate, filtered, cast(Dict[str, float], {}))

    # Округляем до целых
    result = {k: int(round(v)) for k, v in result.items()}

    return json.dumps(result, ensure_ascii=False, indent=2)


# 2. Инвесткопилка


def investment_bank(month: str, transactions: List[Dict[str, Any]], limit: int) -> float:
    """
    Рассчитывает сумму, которую удалось бы отложить в «Инвесткопилку»
    за счёт округления трат.
    """

    # Фильтр: транзакции за нужный месяц
    def matches_month(t: Dict[str, Any]) -> bool:
        date_str = str(t.get("Дата операции", ""))
        try:
            dt = datetime.strptime(date_str.split()[0], "%d.%m.%Y")
            return dt.strftime("%Y-%m") == month
        except (ValueError, IndexError):
            return isinstance(date_str, str) and date_str.startswith(month)

    filtered = filter(matches_month, transactions)

    # Map: считаем разницу между округлённой и фактической суммой
    def calculate_rounding(t: Dict[str, Any]) -> float:
        amount_raw = t.get("Сумма операции", 0)
        try:
            amount = abs(float(amount_raw))
        except (ValueError, TypeError):
            amount = 0.0
        rounded = math.ceil(amount / limit) * limit
        return rounded - amount

    return round(sum(map(calculate_rounding, filtered)), 2)


# 3. Простой поиск


def simple_search(transactions: List[Dict[str, Any]], query: str) -> str:
    """Ищет транзакции, содержащие запрос в описании или категории."""
    query_lower = query.lower()

    found = list(
        filter(
            lambda t: (
                query_lower in str(t.get("Описание", "")).lower() or query_lower in str(t.get("Категория", "")).lower()
            ),
            transactions,
        )
    )

    return json.dumps(found, ensure_ascii=False, indent=2, default=str)


# 4. Поиск по телефонным номерам


def search_by_phone(transactions: List[Dict[str, Any]]) -> str:
    """Ищет транзакции, содержащие мобильные номера в описании."""
    phone_pattern = re.compile(r"\+7\s*\d{3}[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}")

    found = list(filter(lambda t: bool(phone_pattern.search(str(t.get("Описание", "")))), transactions))

    return json.dumps(found, ensure_ascii=False, indent=2, default=str)


# 5. Поиск переводов физическим лицам


def search_transfers_to_individuals(transactions: List[Dict[str, Any]]) -> str:
    """Ищет переводы физическим лицам."""
    name_pattern = re.compile(r"[А-ЯЁ][а-яё]+\s+[А-ЯЁ]\.")

    def is_transfer_to_individual(t: Dict[str, Any]) -> bool:
        category = str(t.get("Категория", ""))
        description = str(t.get("Описание", ""))
        return category == "Переводы" and bool(name_pattern.search(description))

    found = list(filter(is_transfer_to_individual, transactions))

    return json.dumps(found, ensure_ascii=False, indent=2, default=str)


# 6. Дополнительная функция загрузки транзакций из Excel


def load_transactions_from_excel(file_path: str | None = None) -> pd.DataFrame:
    """Загрузить транзакции из Excel файла в виде DataFrame"""
    if file_path is None:
        # Путь по умолчанию
        file_path = str(Path(__file__).parent.parent / "data" / "operations.xls")
    else:
        file_path = str(Path(file_path))

    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Читаем Excel файл и возвращаем сразу DataFrame
    df = pd.read_excel(file_path, engine="calamine")
    return df
