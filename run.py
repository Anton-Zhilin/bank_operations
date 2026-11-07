from src.main import main
from src.reports import spending_by_category, spending_by_weekday, spending_by_workday
from src.services import load_transactions_from_excel

# Загружаем данные
transactions = load_transactions_from_excel()

# Отчёт 1: траты в категории "Супермаркеты" на конец декабря 2021
report1 = spending_by_category(transactions, "Супермаркеты", "2021-12-31")
print(report1)

# Отчёт 2: средние траты по дням недели
report2 = spending_by_weekday(transactions, "2021-12-31")
print(report2)

# Отчёт 3: средние траты в рабочий vs выходной день
report3 = spending_by_workday(transactions, "2021-12-31")
print(report3)

if __name__ == "__main__":
    # Пример локального запуска и проверки
    print(main("2021-12-31 23:59:59"))
