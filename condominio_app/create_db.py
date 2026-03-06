import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment TEXT,
    description TEXT,
    arrival_date TEXT,
    pickup_date TEXT,
    status TEXT
)
""")


cursor.execute("""
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment TEXT,
    password TEXT
)
""")



print("Tabela users criada!")

cursor.execute("""
CREATE TABLE IF NOT EXISTS packages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment TEXT,
    description TEXT,
    arrival_date TEXT,
    pickup_date TEXT,
    status TEXT,
    locker TEXT
)
""")

conn.commit()
conn.close()