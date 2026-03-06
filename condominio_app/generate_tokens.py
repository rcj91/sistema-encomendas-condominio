import sqlite3
import secrets

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT id FROM users")

rows = cursor.fetchall()

for r in rows:

    token = secrets.token_hex(8)

    cursor.execute(
        "UPDATE users SET token=? WHERE id=?",
        (token,r[0])
    )

conn.commit()
conn.close()

print("Tokens gerados")