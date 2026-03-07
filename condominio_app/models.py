import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from config import Config


def get_db():
    """Open a new database connection."""
    conn = sqlite3.connect(Config.DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist and seed default users."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('porteiro', 'morador')),
            email TEXT DEFAULT '',
            apartment TEXT DEFAULT ''
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS packages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartment TEXT NOT NULL,
            description TEXT NOT NULL,
            locker TEXT DEFAULT '',
            arrival_date TEXT NOT NULL,
            pickup_date TEXT,
            status TEXT NOT NULL DEFAULT 'arrived'
                CHECK(status IN ('arrived', 'confirmed', 'picked_up')),
            confirmed_by TEXT,
            confirmed_at TEXT,
            notified INTEGER DEFAULT 0,
            reminder_sent_at TEXT
        )
    """)

    conn.commit()

    # Seed default users if no users exist
    cursor.execute("SELECT COUNT(*) as cnt FROM users")
    if cursor.fetchone()["cnt"] == 0:
        _seed_users(conn)

    conn.close()


def _seed_users(conn):
    """Create default users for the POC."""
    cursor = conn.cursor()
    default_users = [
        ("porteiro", "porteiro123", "porteiro", "porteiro@condominio.com", ""),
        ("101", "morador123", "morador", "morador101@example.com", "101"),
        ("102", "morador123", "morador", "morador102@example.com", "102"),
        ("201", "morador123", "morador", "morador201@example.com", "201"),
    ]
    for username, password, role, email, apartment in default_users:
        cursor.execute(
            """INSERT INTO users (username, password_hash, role, email, apartment)
               VALUES (?, ?, ?, ?, ?)""",
            (username, generate_password_hash(password), role, email, apartment),
        )
    conn.commit()


class User(UserMixin):
    """User model for Flask-Login."""

    def __init__(self, id, username, password_hash, role, email, apartment):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.email = email
        self.apartment = apartment

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        if row:
            return User(
                row["id"], row["username"], row["password_hash"],
                row["role"], row["email"], row["apartment"],
            )
        return None

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        if row:
            return User(
                row["id"], row["username"], row["password_hash"],
                row["role"], row["email"], row["apartment"],
            )
        return None

    @staticmethod
    def get_by_apartment(apartment):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE apartment = ? AND role = 'morador'",
            (apartment,),
        ).fetchone()
        conn.close()
        if row:
            return User(
                row["id"], row["username"], row["password_hash"],
                row["role"], row["email"], row["apartment"],
            )
        return None
