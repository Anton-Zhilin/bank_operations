import json
import os
from datetime import datetime
import pandas as pd

# Импортируем готовые функции из модуля views
from views import get_currency_rates, get_stock_prices, load_user_settings


def get_greeting() -> str:
    """Возвращает приветствие в зависимости от текущего времени суток"""
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return "Доброй ночи"
    elif 6 <= hour < 12:
        return "Доброе утро"
    elif 12 <= hour < 18:
        return "Добрый день"
    else:
        return "Добрый вечер"


def get_cards_stats(transactions: pd.DataFrame) -> list:
    """Рассчитывает статистику по каждой карте: последние 4 цифры, сумма расходов, кэшбэк"""
    # Фильтруем только расходы (отрицательные суммы)
    expenses = transactions[transactions['Сумма платежа'] < 0]
    cards_stats = []

    for card, group in expenses.groupby('Номер карты'):
        total_spent = abs(group['Сумма платежа'].sum())
        cashback = round(total_spent / 100, 2)  # 1 рубль на каждые 100 рублей
        last_digits = str(card).strip()[-4:]

        cards_stats.append({
            "last_digits": last_digits,
            "total_spent": round(total_spent, 2),
            "cashback": cashback
        })

    return cards_stats


def get_top_transactions(transactions: pd.DataFrame, n: int = 5) -> list:
    """Возвращает топ-N транзакций по сумме платежа (по модулю, по убыванию)"""
    top_df = transactions.copy()
    top_df['abs_amount'] = top_df['Сумма платежа'].abs()
    top_df = top_df.sort_values('abs_amount', ascending=False).head(n)

    top_transactions = []
    for _, row in top_df.iterrows():
        top_transactions.append({
            "date": row['Дата операции'].strftime('%d.%m.%Y'),
            "amount": round(float(row['Сумма платежа']), 2),
            "category": str(row['Категория']),
            "description": str(row['Описание'])
        })

    return top_transactions


def main(datetime_str: str) -> str:
    """Главная функция, принимающая строку с датой и временем и возвращающая JSON-ответ. """
    from pathlib import Path

    # 1. Получаем приветствие
    greeting = get_greeting()

    # 2. Загрузка данных - используем правильный путь
    # Получаем корневую папку проекта (на уровень выше src)
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

    # Фильтруем по дате: с начала месяца по указанную дату
    target_date = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
    start_of_month = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    mask = (df['Дата операции'] >= start_of_month) & (df['Дата операции'] <= target_date)
    filtered_df = df[mask]

    # 3. Статистика по картам
    cards_stats = get_cards_stats(filtered_df)

    # 4. Топ-5 транзакций
    top_transactions = get_top_transactions(filtered_df, n=5)

    # 5. Курсы валют и акции (используем функции из views.py)
    settings = load_user_settings()

    # Валюты
    currencies = settings.get("user_currencies", ["USD", "EUR"])
    currency_rates_raw = get_currency_rates(currencies)

    currency_rates = []
    for curr, data in currency_rates_raw.items():
        currency_rates.append({
            "currency": curr,
            "rate": round(data.get('Value', 0.0), 2)
        })

    # Акции
    api_key = os.getenv("ALPHA_VANTAGE_API_KEY", "demo")
    stocks = settings.get("user_stocks", ["AAPL", "AMZN", "GOOGL", "MSFT", "TSLA"])
    stock_prices_raw = get_stock_prices(stocks, api_key)

    stock_prices = []
    for stock, data in stock_prices_raw.items():
        if "error" not in data and "05. price" in data:
            stock_prices.append({
                "stock": stock,
                "price": round(float(data["05. price"]), 2)
            })

    # 6. Формируем итоговый словарь и конвертируем в JSON
    result = {
        "greeting": greeting,
        "cards": cards_stats,
        "top_transactions": top_transactions,
        "currency_rates": currency_rates,
        "stock_prices": stock_prices
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    # Пример локального запуска и проверки
    print(main("2021-12-31 23:59:59"))