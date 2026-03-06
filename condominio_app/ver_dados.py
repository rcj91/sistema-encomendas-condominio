import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM packages")

rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()