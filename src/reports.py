"""Модуль для отчётов по транзакциям"""

from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

import pandas as pd

#  Декоратор для записи результата в файл


def write_to_file(name: str | None = None):
    """Декоратор для записи результата функции в файл"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)

            filename = name if name else f"report_{func.__name__}.txt"
            filepath = Path(__file__).parent.parent / "data" / filename

            with open(filepath, "a", encoding="utf-8") as file:
                file.write(f"{'=' * 60}\n")
                file.write(f"Отчет: {func.__name__}\n")
                file.write(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                file.write(f"{'=' * 60}\n")

                if isinstance(result, pd.DataFrame):
                    if result.empty:
                        file.write("Нет данных за указанный период.\n")
                    else:
                        file.write(result.to_string(index=False))
                else:
                    file.write(str(result))

                file.write("\n\n")

            return result

        return wrapper

    return decorator


#  Вспомогательные функции


def _filter_expenses(transactions: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Внутренняя функция для фильтрации расходов"""
    df = transactions.copy()
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="%d.%m.%Y %H:%M:%S", errors="coerce")

    mask = (df["Дата операции"] >= start_date) & (df["Дата операции"] <= end_date) & (df["Сумма платежа"] < 0)
    return df[mask]


#  Отчёт 1: Траты по категории


@write_to_file()
def spending_by_category(transactions: pd.DataFrame, category: str, date: str | None = None) -> pd.DataFrame:
    end_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    start_date = end_date - timedelta(days=90)  # Последние 3 месяца

    df = _filter_expenses(transactions, start_date, end_date)
    category_df = df[df["Категория"] == category].copy()

    if category_df.empty:
        return pd.DataFrame(columns=["Дата", "Сумма", "Категория", "Описание"])

    category_df["Сумма"] = category_df["Сумма платежа"].abs()
    result = category_df[["Дата операции", "Сумма", "Категория", "Описание"]].copy()
    result.columns = ["Дата", "Сумма", "Категория", "Описание"]
    result = result.sort_values("Дата", ascending=False).reset_index(drop=True)

    return result


#  Отчёт 2: Траты по дням недели


@write_to_file()
def spending_by_weekday(transactions: pd.DataFrame, date: str | None = None) -> pd.DataFrame:
    end_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    start_date = end_date - timedelta(days=90)

    df = _filter_expenses(transactions, start_date, end_date)
    df["Сумма"] = df["Сумма платежа"].abs()
    df["День недели"] = df["Дата операции"].dt.dayofweek

    day_names = {
        0: "Понедельник",
        1: "Вторник",
        2: "Среда",
        3: "Четверг",
        4: "Пятница",
        5: "Суббота",
        6: "Воскресенье",
    }
    df["День недели название"] = df["День недели"].map(day_names)

    result = df.groupby("День недели название")["Сумма"].mean().reset_index()
    result.columns = ["День недели", "Средняя сумма"]
    result["Средняя сумма"] = result["Средняя сумма"].round(2)

    order = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    result["День недели"] = pd.Categorical(result["День недели"], categories=order, ordered=True)
    result = result.sort_values("День недели").reset_index(drop=True)

    return result


#  Отчёт 3: Траты в рабочий / выходной день


@write_to_file()
def spending_by_workday(transactions: pd.DataFrame, date: str | None = None) -> pd.DataFrame:
    end_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
    start_date = end_date - timedelta(days=90)

    df = _filter_expenses(transactions, start_date, end_date)
    df["Сумма"] = df["Сумма платежа"].abs()
    df["День недели"] = df["Дата операции"].dt.dayofweek
    df["Тип дня"] = df["День недели"].apply(lambda x: "Рабочий день" if x < 5 else "Выходной день")

    result = df.groupby("Тип дня")["Сумма"].mean().reset_index()
    result.columns = ["Тип дня", "Средняя сумма"]
    result["Средняя сумма"] = result["Средняя сумма"].round(2)

    order = ["Рабочий день", "Выходной день"]
    result["Тип дня"] = pd.Categorical(result["Тип дня"], categories=order, ordered=True)
    result = result.sort_values("Тип дня").reset_index(drop=True)

    return result
