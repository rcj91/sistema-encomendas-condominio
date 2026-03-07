from flask import Flask, render_template, request, redirect
import sqlite3
from datetime import datetime
import csv
import io
from flask import Response

app = Flask(__name__)


def conectar():
    return sqlite3.connect("database.db")


@app.route("/")
def porteiro():

    q = request.args.get("q","").strip()

    conn = conectar()
    cursor = conn.cursor()

    if q:

        cursor.execute("""
        SELECT * FROM packages
        WHERE status='arrived'
        AND (apartment LIKE ? OR description LIKE ?)
        ORDER BY arrival_date
        """,(f"%{q}%",f"%{q}%"))

    else:

        cursor.execute("""
        SELECT * FROM packages
        WHERE status='arrived'
        ORDER BY arrival_date
        """)

    rows = cursor.fetchall()
    conn.close()

    packages = []

    total = 0
    atrasadas = 0
    hoje = 0

    for r in rows:

        arrival = datetime.fromisoformat(r[3])
        dias = (datetime.now() - arrival).days

        if dias <= 3:
            cor = "table-success"
        elif dias <= 5:
            cor = "table-warning"
        else:
            cor = "table-danger"
            atrasadas += 1

        if dias == 0:
            hoje += 1

        total += 1

        packages.append({
            "id": r[0],
            "apartment": r[1],
            "description": r[2],
            "arrival": r[3],
            "locker": r[6],
            "dias": dias,
            "cor": cor
        })

    stats = {
        "total": total,
        "hoje": hoje,
        "atrasadas": atrasadas
    }

    return render_template("porteiro.html", packages=packages, stats=stats, q=q)


@app.route("/registrar", methods=["POST"])
def registrar():

    apt = request.form["apartment"]
    desc = request.form["description"]
    locker = request.form["locker"]

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO packages
    (apartment,description,locker,arrival_date,status)
    VALUES (?,?,?,?,?)
    """,(apt,desc,locker,datetime.now(),"arrived"))

    conn.commit()
    conn.close()

    return redirect("/")


# @app.route("/retirar/<int:id>")
# def retirar(id):

#     apt = request.args.get("apt")   # ← pega o apartamento da URL

#     conn = conectar()
#     cursor = conn.cursor()

#     cursor.execute("""
#     UPDATE packages
#     SET status='picked_up',
#         pickup_date=?
#     WHERE id=?
#     """,(datetime.now(), id))

#     conn.commit()
#     conn.close()

#     # return redirect(f"/consultar?apt={apt}&msg=ok")
#     return redirect(request.referrer)

@app.route("/retirar/<int:id>")
def retirar(id):

    apt = request.args.get("apt")

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE packages
    SET status='morador_confirmou',
        pickup_date=?
    WHERE id=?
    """,(datetime.now(), id))

    conn.commit()
    conn.close()

    if apt:
        return redirect(f"/consultar?apt={apt}")

    return redirect("/")


@app.route("/morador/<token>")
def morador(token):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT apartment FROM users WHERE token=?",
        (token,)
    )

    user = cursor.fetchone()

    if not user:
        return "Token inválido"

    apt = user[0]

    cursor.execute("""
    SELECT * FROM packages
    WHERE apartment=? AND status='arrived'
    """,(apt,))

    packages = cursor.fetchall()

    conn.close()

    return render_template(
        "morador.html",
        packages=packages,
        apartment=apt
    )


import csv
import io
from flask import Response

@app.route("/historico")
def historico():

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT apartment, description, locker, arrival_date, pickup_date, status
    FROM packages
    ORDER BY arrival_date DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    output = io.StringIO()

    writer = csv.writer(output, delimiter=";")

    writer.writerow([
        "Apartamento",
        "Encomenda (Empresa)",
        "Armário",
        "Data de Chegada",
        "Retirada",
        "Status",
        "Dias na portaria"
    ])

    for r in rows:

        arrival = datetime.fromisoformat(r[3])
        dias = (datetime.now() - arrival).days

        writer.writerow([
            r[0],
            r[1],
            r[2],
            r[3],
            r[4],
            r[5],
            dias
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        '\ufeff' + csv_data,   # ← garante acentos no Excel
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=historico_encomendas.csv"
        }
    )
@app.route("/consultar", methods=["GET","POST"])
def consultar():

    apt = request.args.get("apt")
    msg = request.args.get("msg")
    if request.method == "POST":
        apt = request.form["apartment"]

    if apt:

        conn = conectar()
        cursor = conn.cursor()

        cursor.execute("""
        SELECT *
        FROM packages
        WHERE apartment=? AND status='arrived'
        """,(apt,))

        packages = cursor.fetchall()
        conn.close()

        return render_template(
            "morador.html",
            packages=packages,
            apartment=apt,
            msg=msg
        )

    return render_template("consultar.html")


@app.route("/apagar/<int:id>")
def apagar(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM packages
    WHERE id=? AND status='arrived'
    """,(id,))

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/confirmar/<int:id>")
def confirmar(id):

    conn = conectar()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE packages
    SET status='finalizado'
    WHERE id=?
    """,(id,))

    conn.commit()
    conn.close()

    return redirect("/")




if __name__ == "__main__":
    app.run(debug=True)