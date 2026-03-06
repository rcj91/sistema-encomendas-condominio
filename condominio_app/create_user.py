import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("""
INSERT INTO users (apartment,password)
VALUES (?,?)
""",("302","123"))

conn.commit()
conn.close()

print("Usuário criado com sucesso!")