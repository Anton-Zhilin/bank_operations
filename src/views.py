# src/views.py
"""Модуль для генерации JSON-ответов для веб-страниц"""
import json
from datetime import datetime
from typing import Dict, List, Any
import requests
from pathlib import Path


def get_date_range(end_date: datetime) -> tuple:
    """Получить диапазон дат с начала месяца по входящую дату"""
    start_date = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return start_date, end_date


def load_user_settings() -> Dict[str, Any]:
    """ Загрузить пользовательские настройки из файла """
    settings_path = Path(__file__).parent.parent / "user_settings.json"
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # Возвращаем настройки по умолчанию
        return {
            "user_currencies": ["USD", "EUR"],
            "user_stocks": ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"]
        }


def get_currency_rates(currencies: List[str] = None) -> Dict[str, Dict[str, Any]]:
    """ Получить актуальные курсы валют ЦБ РФ """
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if currencies:
            # Вернуть только запрошенные валюты
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

            # Alpha Vantage возвращает данные в ключе "Global Quote"
            if "Global Quote" in data:
                stock_data[symbol] = data["Global Quote"]
            else:
                stock_data[symbol] = {"error": "No data available"}

        except requests.RequestException as e:
            print(f"Error fetching stock price for {symbol}: {e}")
            stock_data[symbol] = {"error": str(e)}

    return stock_data
