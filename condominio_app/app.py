import csv
import io
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, Response, flash, redirect, render_template, request, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)

from config import Config
from email_service import init_mail, send_package_arrival
from models import User, get_db, init_db
from scheduler import init_scheduler

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Faça login para acessar o sistema."

init_mail(app)

# Initialize database
with app.app_context():
    init_db()


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


# ---------------------------------------------------------------------------
# Role-based access decorators
# ---------------------------------------------------------------------------

def role_required(role):
    """Decorator that restricts access to users with a specific role."""
    def decorator(f):
        @wraps(f)
        @login_required
        def wrapped(*args, **kwargs):
            if current_user.role != role:
                flash("Acesso não autorizado.", "danger")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return wrapped
    return decorator


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    if current_user.is_authenticated:
        if current_user.role == "porteiro":
            return redirect(url_for("porteiro_dashboard"))
        return redirect(url_for("morador_dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = User.get_by_username(username)

        if user and user.check_password(password):
            login_user(user)
            if user.role == "porteiro":
                return redirect(url_for("porteiro_dashboard"))
            return redirect(url_for("morador_dashboard"))

        flash("Usuário ou senha inválidos.", "danger")

    return render_template("new_login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Porteiro routes
# ---------------------------------------------------------------------------

@app.route("/porteiro")
@role_required("porteiro")
def porteiro_dashboard():
    q = request.args.get("q", "").strip()
    conn = get_db()
    cursor = conn.cursor()

    if q:
        cursor.execute(
            """SELECT * FROM packages
               WHERE status IN ('arrived', 'confirmed')
               AND (apartment LIKE ? OR description LIKE ?)
               ORDER BY arrival_date""",
            (f"%{q}%", f"%{q}%"),
        )
    else:
        cursor.execute(
            """SELECT * FROM packages
               WHERE status IN ('arrived', 'confirmed')
               ORDER BY arrival_date"""
        )

    rows = cursor.fetchall()
    conn.close()

    packages = []
    total = 0
    atrasadas = 0
    hoje = 0

    for r in rows:
        arrival = datetime.fromisoformat(r["arrival_date"])
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
            "id": r["id"],
            "apartment": r["apartment"],
            "description": r["description"],
            "arrival": r["arrival_date"],
            "locker": r["locker"],
            "dias": dias,
            "cor": cor,
            "status": r["status"],
            "confirmed_by": r["confirmed_by"],
            "confirmed_at": r["confirmed_at"],
        })

    stats = {"total": total, "hoje": hoje, "atrasadas": atrasadas}
    return render_template(
        "porteiro/dashboard.html", packages=packages, stats=stats, q=q
    )


@app.route("/porteiro/registrar", methods=["POST"])
@role_required("porteiro")
def porteiro_registrar():
    apt = request.form.get("apartment", "").strip()
    desc = request.form.get("description", "").strip()
    locker = request.form.get("locker", "").strip()

    if not apt or not desc:
        flash("Apartamento e descrição são obrigatórios.", "warning")
        return redirect(url_for("porteiro_dashboard"))

    conn = get_db()
    conn.execute(
        """INSERT INTO packages (apartment, description, locker, arrival_date, status)
           VALUES (?, ?, ?, ?, 'arrived')""",
        (apt, desc, locker, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()

    # Send email notification to resident
    resident = User.get_by_apartment(apt)
    if resident and resident.email:
        send_package_arrival(resident.email, apt, desc)

    flash(f"Encomenda registrada para o apartamento {apt}.", "success")
    return redirect(url_for("porteiro_dashboard"))


@app.route("/porteiro/retirar/<int:package_id>")
@role_required("porteiro")
def porteiro_retirar(package_id):
    conn = get_db()
    conn.execute(
        """UPDATE packages SET status='picked_up', pickup_date=?
           WHERE id=?""",
        (datetime.now().isoformat(), package_id),
    )
    conn.commit()
    conn.close()
    flash("Retirada registrada com sucesso.", "success")
    return redirect(url_for("porteiro_dashboard"))


@app.route("/porteiro/historico")
@role_required("porteiro")
def porteiro_historico():
    conn = get_db()
    rows = conn.execute(
        """SELECT apartment, description, locker, arrival_date,
                  pickup_date, status, confirmed_by, confirmed_at
           FROM packages ORDER BY arrival_date DESC"""
    ).fetchall()
    conn.close()

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "Apartamento", "Encomenda (Empresa)", "Armário",
        "Data de Chegada", "Retirada", "Status",
        "Confirmado por", "Confirmação Digital", "Dias na portaria",
    ])

    for r in rows:
        arrival = datetime.fromisoformat(r["arrival_date"])
        dias = (datetime.now() - arrival).days
        writer.writerow([
            r["apartment"], r["description"], r["locker"],
            r["arrival_date"], r["pickup_date"] or "",
            r["status"], r["confirmed_by"] or "",
            r["confirmed_at"] or "", dias,
        ])

    csv_data = output.getvalue()
    output.close()

    return Response(
        "\ufeff" + csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=historico_encomendas.csv"},
    )


# ---------------------------------------------------------------------------
# Morador routes
# ---------------------------------------------------------------------------

@app.route("/morador")
@role_required("morador")
def morador_dashboard():
    apt = current_user.apartment
    conn = get_db()

    pending = conn.execute(
        """SELECT id, description, locker, arrival_date, status, confirmed_by
           FROM packages
           WHERE apartment = ? AND status IN ('arrived', 'confirmed')
           ORDER BY arrival_date""",
        (apt,),
    ).fetchall()

    history = conn.execute(
        """SELECT description, locker, arrival_date, pickup_date, confirmed_by
           FROM packages
           WHERE apartment = ? AND status = 'picked_up'
           ORDER BY pickup_date DESC
           LIMIT 20""",
        (apt,),
    ).fetchall()
    conn.close()

    pending_list = []
    for p in pending:
        arrival = datetime.fromisoformat(p["arrival_date"])
        dias = (datetime.now() - arrival).days
        pending_list.append({
            "id": p["id"],
            "description": p["description"],
            "locker": p["locker"],
            "arrival_date": p["arrival_date"],
            "status": p["status"],
            "dias": dias,
        })

    history_list = [dict(h) for h in history]

    return render_template(
        "morador/dashboard.html", pending=pending_list, history=history_list
    )


@app.route("/morador/confirmar/<int:package_id>", methods=["POST"])
@role_required("morador")
def morador_confirmar(package_id):
    apt = current_user.apartment
    conn = get_db()

    # Verify the package belongs to this resident
    pkg = conn.execute(
        "SELECT * FROM packages WHERE id = ? AND apartment = ?",
        (package_id, apt),
    ).fetchone()

    if not pkg:
        flash("Encomenda não encontrada.", "danger")
        conn.close()
        return redirect(url_for("morador_dashboard"))

    if pkg["status"] == "picked_up":
        flash("Esta encomenda já foi retirada.", "info")
        conn.close()
        return redirect(url_for("morador_dashboard"))

    conn.execute(
        """UPDATE packages
           SET status = 'confirmed',
               confirmed_by = ?,
               confirmed_at = ?
           WHERE id = ?""",
        (f"Apto {apt}", datetime.now().isoformat(), package_id),
    )
    conn.commit()
    conn.close()

    flash("Retirada confirmada digitalmente! ✅", "success")
    return redirect(url_for("morador_dashboard"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_scheduler(app)
    app.run(debug=False, host="0.0.0.0", port=5000)