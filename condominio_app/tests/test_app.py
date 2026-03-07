"""Tests for the condominium package management system."""
import os
import sys
import tempfile

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
        assert "Acesso ao Sistema".encode() in resp.data

    def test_login_porteiro_success(self, client):
        resp = _login(client, "porteiro", "porteiro123")
        assert resp.status_code == 200
        assert "Portaria".encode() in resp.data

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
# Porteiro routes tests
# ---------------------------------------------------------------------------

class TestPorteiro:
    def test_dashboard_loads(self, client):
        _login(client, "porteiro", "porteiro123")
        resp = client.get("/porteiro")
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
        # Register a package first
        client.post(
            "/porteiro/registrar",
            data={"apartment": "102", "description": "Mercado Livre", "locker": "B2"},
        )
        # Pick it up
        resp = client.get("/porteiro/retirar/1", follow_redirects=True)
        assert resp.status_code == 200

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
        # Porteiro registers a package
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "101", "description": "Shopee", "locker": "D4"},
        )
        client.get("/logout")

        # Morador confirms pickup
        _login(client, "101", "morador123")
        resp = client.post("/morador/confirmar/1", follow_redirects=True)
        assert resp.status_code == 200
        assert "Confirmado".encode() in resp.data or "confirmada".encode() in resp.data

    def test_cannot_confirm_other_apartment(self, client):
        # Porteiro registers for apt 102
        _login(client, "porteiro", "porteiro123")
        client.post(
            "/porteiro/registrar",
            data={"apartment": "102", "description": "DHL", "locker": "E5"},
        )
        client.get("/logout")

        # Morador 101 tries to confirm apt 102's package
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
