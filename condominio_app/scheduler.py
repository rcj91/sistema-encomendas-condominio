import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_db, User
from email_service import send_pending_reminder

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def send_daily_reminders(app):
    """Check for pending packages and send reminder emails."""
    with app.app_context():
        logger.info("Executando verificação de encomendas pendentes...")
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT apartment, id, description, arrival_date
            FROM packages
            WHERE status = 'arrived'
            ORDER BY apartment
        """)
        rows = cursor.fetchall()
        conn.close()

        # Group packages by apartment
        by_apartment = {}
        for row in rows:
            apt = row["apartment"]
            arrival = datetime.fromisoformat(row["arrival_date"])
            dias = (datetime.now() - arrival).days
            if dias < 1:
                continue
            if apt not in by_apartment:
                by_apartment[apt] = []
            by_apartment[apt].append({
                "id": row["id"],
                "description": row["description"],
                "arrival_date": row["arrival_date"],
                "dias": dias,
            })

        for apt, packages in by_apartment.items():
            user = User.get_by_apartment(apt)
            if user and user.email:
                send_pending_reminder(user.email, apt, packages)
                logger.info(
                    "Lembrete enviado para apto %s (%d encomenda(s))",
                    apt, len(packages),
                )

        logger.info("Verificação concluída. %d apartamento(s) notificado(s).",
                     len(by_apartment))


def init_scheduler(app):
    """Initialize the background scheduler for daily reminders."""
    scheduler.add_job(
        func=send_daily_reminders,
        args=[app],
        trigger="cron",
        hour=app.config.get("SCHEDULER_HOUR", 8),
        minute=app.config.get("SCHEDULER_MINUTE", 0),
        id="daily_reminders",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler iniciado — lembretes diários configurados.")
