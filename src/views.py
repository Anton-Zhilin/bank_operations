"""Модуль для генерации JSON-ответов для веб-страниц"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
import requests
from pathlib import Path
from bisect import bisect


def get_greeting() -> str:
    """Возвращает приветствие в зависимости от времени суток"""
    hour = datetime.now().hour
    boundaries = [0, 6, 12, 18]
    greetings = ['Доброй ночи', 'Доброе утро', 'Добрый день', 'Добрый вечер']
    return greetings[bisect(boundaries, hour) - 1]


def get_date_range(end_date: datetime, period: str = 'M') -> tuple:
    """Получить диапазон дат в зависимости от периода"""
    end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

    if period == 'W':
        start_date = end_date - timedelta(days=end_date.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'M':
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'Y':
        start_date = end_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    elif period == 'ALL':
        start_date = datetime(1900, 1, 1, 0, 0, 0, 0)
    else:
        start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    return start_date, end_date


def load_user_settings() -> Dict[str, Any]:
    """Загрузить пользовательские настройки из файла"""
    settings_path = Path(__file__).parent.parent / "user_settings.json"
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        }


def get_currency_rates(currencies: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """Получить актуальные курсы валют ЦБ РФ"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if currencies:
            return {
                curr: data['Valute'].get(curr, {})
                for curr in currencies
                if curr in data['Valute']
            }
        return data['Valute']
    except requests.RequestException as e:
        print(f"Error fetching currency rates: {e}")
        return {}


def get_stock_prices(symbols: List[str], api_key: str) -> Dict[str, Dict[str, Any]]:
    """Получить текущие цены акций через Alpha Vantage API"""
    base_url = "https://www.alphavantage.co/query"
    stock_data = {}

    for symbol in symbols:
        try:
            params = {
                'function': 'GLOBAL_QUOTE',
                'symbol': symbol,
                'apikey': api_key
            }
            response = requests.get(base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if "Global Quote" in data:
                stock_data[symbol] = data["Global Quote"]
            else:
                stock_data[symbol] = {"error": "No data available"}

        except requests.RequestException as e:
            print(f"Error fetching stock price for {symbol}: {e}")
            stock_data[symbol] = {"error": str(e)}

    return stock_data


def events_page(date_str: str, period: str = 'M') -> str:
    """Главная функция страницы "События"."""
    from pathlib import Path

    # 1. Парсинг даты и получение диапазона
    target_date = datetime.strptime(date_str, "%Y-%m-%d")
    start_date, end_date = get_date_range(target_date, period)

    # 2. Загрузка и фильтрация данных - используем правильный путь
    project_root = Path(__file__).parent.parent
    file_path = project_root / "data" / "operations.xls"

    if not file_path.exists():
        raise FileNotFoundError(f"Файл не найден: {file_path}")

    df = pd.read_excel(file_path, engine='calamine')

    # Преобразуем столбец с датой в формат datetime
    df['Дата операции'] = pd.to_datetime(
        df['Дата операции'],
        format='%d.%m.%Y %H:%M:%S',
        errors='coerce'
    )

    # Фильтруем по дате
    mask = (df['Дата операции'] >= start_date) & (df['Дата операции'] <= end_date)
    filtered_df = df[mask].copy()

    # 3. Обработка расходов (Сумма платежа < 0)
    expenses_df = filtered_df[filtered_df['Сумма платежа'] < 0].copy()
    expenses_df['abs_amount'] = expenses_df['Сумма платежа'].abs()

    total_expenses = int(round(expenses_df['abs_amount'].sum())) if not expenses_df.empty else 0

    # 3.1. Переводы и наличные (отдельная категория)
    tc_categories = ['Наличные', 'Переводы']
    tc_df = expenses_df[expenses_df['Категория'].isin(tc_categories)]
    tc_grouped = tc_df.groupby('Категория')['abs_amount'].sum().reset_index()
    tc_grouped = tc_grouped.sort_values('abs_amount', ascending=False)

    transfers_and_cash = [
        {"category": row['Категория'], "amount": int(round(row['abs_amount']))}
        for _, row in tc_grouped.iterrows()
    ]

    # 3.2. Основные траты (исключаем Наличные и Переводы)
    main_exp_df = expenses_df[~expenses_df['Категория'].isin(tc_categories)]
    main_grouped = main_exp_df.groupby('Категория')['abs_amount'].sum().reset_index()
    main_grouped = main_grouped.sort_values('abs_amount', ascending=False)

    main_expenses = []
    other_amount = 0.0

    for i, (_, row) in enumerate(main_grouped.iterrows()):
        if i < 7:
            main_expenses.append({
                "category": row['Категория'],
                "amount": int(round(row['abs_amount']))
            })
        else:
            other_amount += row['abs_amount']

    if other_amount > 0:
        main_expenses.append({
            "category": "Остальное",
            "amount": int(round(other_amount))
        })

    # 4. Обработка поступлений (Сумма платежа > 0)
    income_df = filtered_df[filtered_df['Сумма платежа'] > 0].copy()
    total_income = int(round(income_df['Сумма платежа'].sum())) if not income_df.empty else 0

    income_grouped = income_df.groupby('Категория')['Сумма платежа'].sum().reset_index()
    income_grouped = income_grouped.sort_values('Сумма платежа', ascending=False)

    main_income = [
        {"category": row['Категория'], "amount": int(round(row['Сумма платежа']))}
        for _, row in income_grouped.iterrows()
    ]

    # 5. Курсы валют и акции
    settings = load_user_settings()

    currency_rates_raw = get_currency_rates(settings.get("user_currencies", ["USD", "EUR"]))
    currency_rates = [
        {"currency": k, "rate": round(v.get('Value', 0.0), 2)}
        for k, v in currency_rates_raw.items()
    ]

    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    stock_prices_raw = get_stock_prices(settings.get("user_stocks", []), api_key)
    stock_prices = [
        {"stock": k, "price": round(float(v.get("05. price", 0)), 2)}
        for k, v in stock_prices_raw.items() if "05. price" in v
    ]

    # 6. Формирование итогового JSON
    result = {
        "expenses": {
            "total_amount": total_expenses,
            "main": main_expenses,
            "transfers_and_cash": transfers_and_cash
        },
        "income": {
            "total_amount": total_income,
            "main": main_income
        },
        "currency_rates": currency_rates,
        "stock_prices": stock_prices
    }

    return json.dumps(result, ensure_ascii=False, indent=2)

if __name__ == "__main__":

    print("Тест за месяц (M)")
    print(events_page("2021-12-31", "M"))
    print("\nТест за год (Y)")
    print(events_page("2021-12-31", "Y"))