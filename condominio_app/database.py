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

conn.commit()
conn.close()

print("Banco criado!")