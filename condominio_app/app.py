import csv
import io
import logging
import os
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
from werkzeug.security import generate_password_hash

from config import Config
from email_service import init_mail, send_package_arrival, send_pending_reminder
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
# Porteiro — Dashboard
# ---------------------------------------------------------------------------

@app.route("/porteiro")
@role_required("porteiro")
def porteiro_dashboard():
    conn = get_db()

    # Stats
    total_pending = conn.execute(
        "SELECT COUNT(*) as c FROM packages WHERE status IN ('arrived','confirmed')"
    ).fetchone()["c"]
    total_today = conn.execute(
        "SELECT COUNT(*) as c FROM packages WHERE date(arrival_date)=date('now')"
    ).fetchone()["c"]
    total_overdue = conn.execute(
        "SELECT COUNT(*) as c FROM packages WHERE status IN ('arrived','confirmed') "
        "AND julianday('now')-julianday(arrival_date) > 5"
    ).fetchone()["c"]
    total_picked = conn.execute(
        "SELECT COUNT(*) as c FROM packages WHERE status='picked_up'"
    ).fetchone()["c"]
    total_users = conn.execute(
        "SELECT COUNT(*) as c FROM users WHERE role='morador'"
    ).fetchone()["c"]
    total_emails = conn.execute(
        "SELECT COUNT(*) as c FROM email_logs"
    ).fetchone()["c"]

    # Recent packages (last 10)
    recent = conn.execute(
        """SELECT * FROM packages ORDER BY arrival_date DESC LIMIT 10"""
    ).fetchall()
    conn.close()

    recent_list = []
    for r in recent:
        arrival = datetime.fromisoformat(r["arrival_date"])
        dias = (datetime.now() - arrival).days
        recent_list.append({
            "id": r["id"],
            "apartment": r["apartment"],
            "description": r["description"],
            "arrival": r["arrival_date"],
            "locker": r["locker"],
            "dias": dias,
            "status": r["status"],
        })

    stats = {
        "total_pending": total_pending,
        "total_today": total_today,
        "total_overdue": total_overdue,
        "total_picked": total_picked,
        "total_users": total_users,
        "total_emails": total_emails,
    }
    return render_template("porteiro/dashboard.html", stats=stats, recent=recent_list)


# ---------------------------------------------------------------------------
# Porteiro — Encomendas (Packages CRUD)
# ---------------------------------------------------------------------------

@app.route("/porteiro/encomendas")
@role_required("porteiro")
def porteiro_encomendas():
    q = request.args.get("q", "").strip()
    conn = get_db()

    if q:
        rows = conn.execute(
            """SELECT * FROM packages
               WHERE status IN ('arrived', 'confirmed')
               AND (apartment LIKE ? OR description LIKE ?)
               ORDER BY arrival_date""",
            (f"%{q}%", f"%{q}%"),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT * FROM packages
               WHERE status IN ('arrived', 'confirmed')
               ORDER BY arrival_date"""
        ).fetchall()
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

    pkg_stats = {"total": total, "hoje": hoje, "atrasadas": atrasadas}
    return render_template(
        "porteiro/encomendas.html", packages=packages, stats=pkg_stats, q=q
    )


@app.route("/porteiro/registrar", methods=["POST"])
@role_required("porteiro")
def porteiro_registrar():
    apt = request.form.get("apartment", "").strip()
    desc = request.form.get("description", "").strip()
    locker = request.form.get("locker", "").strip()

    if not apt or not desc:
        flash("Apartamento e descrição são obrigatórios.", "warning")
        return redirect(url_for("porteiro_encomendas"))

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
        send_package_arrival(resident.email, apt, desc, triggered_by="registro")

    flash(f"Encomenda registrada para o apartamento {apt}.", "success")
    return redirect(url_for("porteiro_encomendas"))


@app.route("/porteiro/retirar/<int:package_id>", methods=["POST"])
@role_required("porteiro")
def porteiro_retirar(package_id):
    conn = get_db()
    pkg = conn.execute(
        "SELECT * FROM packages WHERE id = ?", (package_id,)
    ).fetchone()

    if not pkg:
        flash("Encomenda não encontrada.", "danger")
        conn.close()
        return redirect(url_for("porteiro_encomendas"))

    if pkg["status"] == "picked_up":
        flash("Esta encomenda já foi retirada.", "info")
        conn.close()
        return redirect(url_for("porteiro_encomendas"))

    conn.execute(
        """UPDATE packages SET status='picked_up', pickup_date=?
           WHERE id=?""",
        (datetime.now().isoformat(), package_id),
    )
    conn.commit()
    conn.close()
    flash("Retirada registrada com sucesso.", "success")
    return redirect(url_for("porteiro_encomendas"))


@app.route("/porteiro/notificar/<int:package_id>", methods=["POST"])
@role_required("porteiro")
def porteiro_notificar(package_id):
    """Manually send an email reminder for a specific package."""
    conn = get_db()
    pkg = conn.execute(
        "SELECT * FROM packages WHERE id = ?", (package_id,)
    ).fetchone()

    if not pkg:
        flash("Encomenda não encontrada.", "danger")
        conn.close()
        return redirect(url_for("porteiro_encomendas"))

    if pkg["status"] == "picked_up":
        flash("Esta encomenda já foi retirada.", "info")
        conn.close()
        return redirect(url_for("porteiro_encomendas"))

    apt = pkg["apartment"]
    resident = User.get_by_apartment(apt)

    if not resident or not resident.email:
        flash(f"Morador do apto {apt} não possui e-mail cadastrado.", "warning")
        conn.close()
        return redirect(url_for("porteiro_encomendas"))

    arrival = datetime.fromisoformat(pkg["arrival_date"])
    dias = (datetime.now() - arrival).days
    packages_info = [{
        "description": pkg["description"],
        "arrival_date": pkg["arrival_date"],
        "dias": dias,
    }]
    send_pending_reminder(
        resident.email, apt, packages_info, triggered_by="manual (porteiro)"
    )

    flash(f"Notificação enviada por e-mail para o morador do apto {apt}.", "success")
    conn.close()
    return redirect(url_for("porteiro_encomendas"))


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
# Porteiro — User Management
# ---------------------------------------------------------------------------

@app.route("/porteiro/usuarios")
@role_required("porteiro")
def porteiro_usuarios():
    conn = get_db()
    users = conn.execute(
        "SELECT * FROM users ORDER BY role, apartment, username"
    ).fetchall()
    conn.close()
    return render_template("porteiro/usuarios.html", users=users)


@app.route("/porteiro/usuarios/novo", methods=["GET", "POST"])
@role_required("porteiro")
def porteiro_usuario_novo():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "morador")
        email = request.form.get("email", "").strip()
        apartment = request.form.get("apartment", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        block = request.form.get("block", "").strip()

        if not username or not password:
            flash("Usuário e senha são obrigatórios.", "warning")
            return render_template("porteiro/usuario_form.html", user=None)

        if User.get_by_username(username):
            flash("Este nome de usuário já existe.", "danger")
            return render_template("porteiro/usuario_form.html", user=None)

        conn = get_db()
        conn.execute(
            """INSERT INTO users
               (username, password_hash, role, email, apartment, name, phone, block)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, generate_password_hash(password), role, email,
             apartment, name, phone, block),
        )
        conn.commit()
        conn.close()
        flash(f"Usuário '{username}' criado com sucesso.", "success")
        return redirect(url_for("porteiro_usuarios"))

    return render_template("porteiro/usuario_form.html", user=None)


@app.route("/porteiro/usuarios/<int:user_id>/editar", methods=["GET", "POST"])
@role_required("porteiro")
def porteiro_usuario_editar(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

    if not row:
        conn.close()
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("porteiro_usuarios"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        apartment = request.form.get("apartment", "").strip()
        name = request.form.get("name", "").strip()
        phone = request.form.get("phone", "").strip()
        block = request.form.get("block", "").strip()
        role = request.form.get("role", row["role"])
        new_password = request.form.get("password", "").strip()

        if new_password:
            conn.execute(
                """UPDATE users SET email=?, apartment=?, name=?, phone=?,
                   block=?, role=?, password_hash=? WHERE id=?""",
                (email, apartment, name, phone, block, role,
                 generate_password_hash(new_password), user_id),
            )
        else:
            conn.execute(
                """UPDATE users SET email=?, apartment=?, name=?, phone=?,
                   block=?, role=? WHERE id=?""",
                (email, apartment, name, phone, block, role, user_id),
            )
        conn.commit()
        conn.close()
        flash("Usuário atualizado com sucesso.", "success")
        return redirect(url_for("porteiro_usuarios"))

    conn.close()
    return render_template("porteiro/usuario_form.html", user=dict(row))


@app.route("/porteiro/usuarios/<int:user_id>/excluir", methods=["POST"])
@role_required("porteiro")
def porteiro_usuario_excluir(user_id):
    if user_id == current_user.id:
        flash("Você não pode excluir seu próprio usuário.", "danger")
        return redirect(url_for("porteiro_usuarios"))

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    flash("Usuário excluído com sucesso.", "success")
    return redirect(url_for("porteiro_usuarios"))


# ---------------------------------------------------------------------------
# Porteiro — Email Management
# ---------------------------------------------------------------------------

@app.route("/porteiro/emails")
@role_required("porteiro")
def porteiro_emails():
    conn = get_db()
    logs = conn.execute(
        "SELECT * FROM email_logs ORDER BY sent_at DESC LIMIT 100"
    ).fetchall()
    conn.close()
    return render_template("porteiro/emails.html", logs=logs)


# ---------------------------------------------------------------------------
# Porteiro — Reports
# ---------------------------------------------------------------------------

@app.route("/porteiro/relatorios")
@role_required("porteiro")
def porteiro_relatorios():
    conn = get_db()

    # Packages per apartment
    per_apt = conn.execute(
        """SELECT apartment, COUNT(*) as total,
                  SUM(CASE WHEN status='picked_up' THEN 1 ELSE 0 END) as retiradas,
                  SUM(CASE WHEN status IN ('arrived','confirmed') THEN 1 ELSE 0 END) as pendentes
           FROM packages GROUP BY apartment ORDER BY total DESC"""
    ).fetchall()

    # Average time to pickup
    avg_time = conn.execute(
        """SELECT ROUND(AVG(julianday(pickup_date)-julianday(arrival_date)), 1) as avg_days
           FROM packages WHERE status='picked_up' AND pickup_date IS NOT NULL"""
    ).fetchone()

    # Monthly volume
    monthly = conn.execute(
        """SELECT strftime('%Y-%m', arrival_date) as month, COUNT(*) as total
           FROM packages GROUP BY month ORDER BY month DESC LIMIT 12"""
    ).fetchall()

    # Top carriers
    top_carriers = conn.execute(
        """SELECT description, COUNT(*) as total
           FROM packages GROUP BY description ORDER BY total DESC LIMIT 10"""
    ).fetchall()

    # Status breakdown
    status_breakdown = conn.execute(
        """SELECT status, COUNT(*) as total FROM packages GROUP BY status"""
    ).fetchall()

    conn.close()

    return render_template(
        "porteiro/relatorios.html",
        per_apt=per_apt,
        avg_days=avg_time["avg_days"] if avg_time["avg_days"] else 0,
        monthly=monthly,
        top_carriers=top_carriers,
        status_breakdown=status_breakdown,
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

    flash("Retirada confirmada digitalmente!", "success")
    return redirect(url_for("morador_dashboard"))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_scheduler(app)
    host = os.environ.get("FLASK_HOST", "127.0.0.1")
    port = int(os.environ.get("FLASK_PORT", 5001))
    app.run(debug=False, host=host, port=port)