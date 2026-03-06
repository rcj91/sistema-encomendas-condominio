import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("ALTER TABLE packages ADD COLUMN locker TEXT")

conn.commit()
conn.close()

print("Coluna locker adicionada com sucesso!")