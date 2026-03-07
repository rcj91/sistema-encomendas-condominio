import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    # In production, set SECRET_KEY via environment variable to persist sessions
    # across restarts. The fallback is a static placeholder suitable only for
    # local development/POC usage.
    SECRET_KEY = os.environ.get("SECRET_KEY", "poc-dev-secret-change-in-production")
    DATABASE = os.path.join(BASE_DIR, "database.db")

    # Flask-Mail settings — configure with real SMTP for production
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "localhost")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "true").lower() == "true"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get(
        "MAIL_DEFAULT_SENDER", "condominio@example.com"
    )

    # Scheduler
    SCHEDULER_HOUR = int(os.environ.get("SCHEDULER_HOUR", 8))
    SCHEDULER_MINUTE = int(os.environ.get("SCHEDULER_MINUTE", 0))
