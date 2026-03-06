import sqlite3
import qrcode

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute("SELECT apartment,token FROM users")

rows = cursor.fetchall()

for r in rows:

    apt = r[0]
    token = r[1]

    url = f"http://127.0.0.1:5000/morador/{token}"

    img = qrcode.make(url)

    img.save(f"qr_apto_{apt}.png")

print("QRs criados")