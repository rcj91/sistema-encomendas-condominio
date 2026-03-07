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
            apartment TEXT DEFAULT '',
            name TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            block TEXT DEFAULT ''
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

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_email TEXT NOT NULL,
            apartment TEXT DEFAULT '',
            subject TEXT NOT NULL,
            body TEXT DEFAULT '',
            sent_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'sent',
            triggered_by TEXT DEFAULT ''
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
        ("porteiro", "porteiro123", "porteiro", "porteiro@condominio.com",
         "", "João da Silva", "(11) 99999-0000", ""),
        ("101", "morador123", "morador", "morador101@example.com",
         "101", "Maria Souza", "(11) 98888-1111", "A"),
        ("102", "morador123", "morador", "morador102@example.com",
         "102", "Carlos Oliveira", "(11) 97777-2222", "A"),
        ("201", "morador123", "morador", "morador201@example.com",
         "201", "Ana Santos", "(11) 96666-3333", "B"),
    ]
    for username, password, role, email, apartment, name, phone, block in default_users:
        cursor.execute(
            """INSERT INTO users
               (username, password_hash, role, email, apartment, name, phone, block)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, generate_password_hash(password), role, email,
             apartment, name, phone, block),
        )
    conn.commit()


def log_email(recipient_email, apartment, subject, body, triggered_by, status="sent"):
    """Log an email to the database."""
    from datetime import datetime
    conn = get_db()
    conn.execute(
        """INSERT INTO email_logs
           (recipient_email, apartment, subject, body, sent_at, status, triggered_by)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (recipient_email, apartment, subject, body,
         datetime.now().isoformat(), status, triggered_by),
    )
    conn.commit()
    conn.close()


class User(UserMixin):
    """User model for Flask-Login."""

    def __init__(self, id, username, password_hash, role, email, apartment,
                 name="", phone="", block=""):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.role = role
        self.email = email
        self.apartment = apartment
        self.name = name
        self.phone = phone
        self.block = block

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def _from_row(row):
        """Build a User from a database row, handling optional columns."""
        if not row:
            return None
        return User(
            row["id"], row["username"], row["password_hash"],
            row["role"], row["email"], row["apartment"],
            row["name"] if "name" in row.keys() else "",
            row["phone"] if "phone" in row.keys() else "",
            row["block"] if "block" in row.keys() else "",
        )

    @staticmethod
    def get_by_id(user_id):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE id = ?", (user_id,)
        ).fetchone()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_by_username(username):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        return User._from_row(row)

    @staticmethod
    def get_by_apartment(apartment):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE apartment = ? AND role = 'morador'",
            (apartment,),
        ).fetchone()
        conn.close()
        return User._from_row(row)
