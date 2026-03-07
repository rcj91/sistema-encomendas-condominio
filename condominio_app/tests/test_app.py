"""Tests for the condominium package management system."""
import os
import sys

import pytest

# Ensure condominio_app is importable
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), os.pardir)
)

from config import Config  # noqa: E402


@pytest.fixture(autouse=True)
def _temp_db(tmp_path, monkeypatch):
    """Use a temporary database for every test."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(Config, "DATABASE", db_path)
    # Re-import after patching to ensure init_db uses temp db
    from models import init_db
    init_db()
    yield db_path


@pytest.fixture()
def app():
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    yield flask_app


@pytest.fixture()
def client(app):
    return app.test_client()


def _login(client, username, password):
    return client.post(
        "/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


# ---------------------------------------------------------------------------
# Authentication tests
# ---------------------------------------------------------------------------

class TestAuth:
    def test_login_page_loads(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200
        assert "Sistema de Encomendas".encode() in resp.data

    def test_login_porteiro_success(self, client):
        resp = _login(client, "porteiro", "porteiro123")
        assert resp.status_code == 200
        assert "Dashboard".encode() in resp.data

    def test_login_morador_success(self, client):
        resp = _login(client, "101", "morador123")
        assert resp.status_code == 200
        assert "Minhas Encomendas".encode() in resp.data

    def test_login_invalid_credentials(self, client):
        resp = _login(client, "porteiro", "wrongpassword")
        assert "inválidos".encode() in resp.data

    def test_logout(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/logout", follow_redirects=True)
        assert "saiu".encode() in resp.data

    def test_unauthenticated_redirect(self, client):
        resp = client.get("/porteiro")
        assert resp.status_code == 302


# ---------------------------------------------------------------------------
# Porteiro Dashboard tests
# ---------------------------------------------------------------------------

class TestPorteiroDashboard:
    def test_dashboard_loads(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro")
        assert resp.status_code == 200
        assert "Dashboard".encode() in resp.data

    def test_dashboard_shows_stats(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro")
        assert resp.status_code == 200
        assert "Pendentes".encode() in resp.data


# ---------------------------------------------------------------------------
# Porteiro Encomendas tests
# ---------------------------------------------------------------------------

class TestPorteiroEncomendas:
    def test_encomendas_loads(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro/encomendas")
        assert resp.status_code == 200
        assert "Registrar".encode() in resp.data

    def test_register_package(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post(
            "/porteiro/registrar",
            data={"apartment": "101", "description": "Amazon", "locker": "A1"},
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "101".encode() in resp.data
        assert "Amazon".encode() in resp.data

    def test_register_package_validation(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post(
            "/porteiro/registrar",
            data={"apartment": "", "description": "", "locker": ""},
            follow_redirects=True,
        )
        assert "obrigatórios".encode() in resp.data

    def test_pickup_package(self, client):
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "102", "description": "Mercado Livre", "locker": "B2"},
        )
        resp = client.post("/porteiro/retirar/1", follow_redirects=True)
        assert resp.status_code == 200

    def test_pickup_nonexistent(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post("/porteiro/retirar/999", follow_redirects=True)
        assert "não encontrada".encode() in resp.data

    def test_historico_csv(self, client):
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "201", "description": "Correios", "locker": "C3"},
        )
        resp = client.get("/porteiro/historico")
        assert resp.status_code == 200
        assert "text/csv" in resp.content_type
        assert "Apartamento".encode() in resp.data

    def test_morador_cannot_access_porteiro(self, client):
        _login(client, "101", "morador123")
        resp = client.get("/porteiro", follow_redirects=True)
        assert "não autorizado".encode() in resp.data

    def test_notify_package(self, client):
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "101", "description": "Shopee", "locker": "D4"},
        )
        resp = client.post("/porteiro/notificar/1", follow_redirects=True)
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Porteiro User Management tests
# ---------------------------------------------------------------------------

class TestPorteiroUsuarios:
    def test_list_users(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro/usuarios")
        assert resp.status_code == 200
        assert "porteiro".encode() in resp.data

    def test_create_user(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post(
            "/porteiro/usuarios/novo",
            data={
                "username": "301", "password": "pass123",
                "role": "morador", "email": "m301@test.com",
                "apartment": "301", "name": "Test User",
                "phone": "11999990000", "block": "C",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "301".encode() in resp.data

    def test_create_user_duplicate(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post(
            "/porteiro/usuarios/novo",
            data={
                "username": "101", "password": "pass",
                "role": "morador", "email": "", "apartment": "101",
                "name": "", "phone": "", "block": "",
            },
            follow_redirects=True,
        )
        assert "já existe".encode() in resp.data

    def test_edit_user(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro/usuarios/2/editar")
        assert resp.status_code == 200
        resp = client.post(
            "/porteiro/usuarios/2/editar",
            data={
                "email": "new@test.com", "apartment": "101",
                "name": "Updated", "phone": "1100000",
                "block": "A", "role": "morador", "password": "",
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert "atualizado".encode() in resp.data

    def test_delete_user(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post("/porteiro/usuarios/3/excluir", follow_redirects=True)
        assert resp.status_code == 200
        assert "excluído".encode() in resp.data

    def test_cannot_delete_self(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.post("/porteiro/usuarios/1/excluir", follow_redirects=True)
        assert "não pode excluir".encode() in resp.data


# ---------------------------------------------------------------------------
# Porteiro Email Management tests
# ---------------------------------------------------------------------------

class TestPorteiroEmails:
    def test_email_log_page(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro/emails")
        assert resp.status_code == 200
        assert "E-mails".encode() in resp.data


# ---------------------------------------------------------------------------
# Porteiro Reports tests
# ---------------------------------------------------------------------------

class TestPorteiroRelatorios:
    def test_reports_page(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro/relatorios")
        assert resp.status_code == 200
        assert "Relatórios".encode() in resp.data or "Estat".encode() in resp.data


# ---------------------------------------------------------------------------
# Morador routes tests
# ---------------------------------------------------------------------------

class TestMorador:
    def test_dashboard_loads(self, client):
        _login(client, "101", "morador123")
        resp = client.get("/morador")
        assert resp.status_code == 200
        assert "Minhas Encomendas".encode() in resp.data

    def test_confirm_pickup(self, client):
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "101", "description": "Shopee", "locker": "D4"},
        )
        client.get("/logout")

        _login(client, "101", "morador123")
        resp = client.post("/morador/confirmar/1", follow_redirects=True)
        assert resp.status_code == 200
        assert "Confirmado".encode() in resp.data or "confirmada".encode() in resp.data

    def test_cannot_confirm_other_apartment(self, client):
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "102", "description": "DHL", "locker": "E5"},
        )
        client.get("/logout")

        _login(client, "101", "morador123")
        resp = client.post("/morador/confirmar/1", follow_redirects=True)
        assert "não encontrada".encode() in resp.data

    def test_porteiro_cannot_access_morador(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/morador", follow_redirects=True)
        assert "não autorizado".encode() in resp.data


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestModels:
    def test_user_get_by_username(self):
        from models import User
        user = User.get_by_username("porteiro")
        assert user is not None
        assert user.role == "porteiro"

    def test_user_get_by_apartment(self):
        from models import User
        user = User.get_by_apartment("101")
        assert user is not None
        assert user.role == "morador"

    def test_user_check_password(self):
        from models import User
        user = User.get_by_username("porteiro")
        assert user.check_password("porteiro123")
        assert not user.check_password("wrong")

    def test_user_get_nonexistent(self):
        from models import User
        assert User.get_by_username("nobody") is None
        assert User.get_by_id(9999) is None

    def test_user_has_extended_fields(self):
        from models import User
        user = User.get_by_username("porteiro")
        assert hasattr(user, "name")
        assert hasattr(user, "phone")
        assert hasattr(user, "block")
