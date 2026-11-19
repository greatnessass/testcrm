import sqlite3

# Подключаемся к базе
conn = sqlite3.connect("crm.db")
cursor = conn.cursor()

# Читаем наш SQL
with open("scripts/seed.sql", "r", encoding="utf-8") as f:
    sql = f.read()

# Выполняем
cursor.executescript(sql)
conn.commit()
conn.close()

print("Данные успешно загружены!")