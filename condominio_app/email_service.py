import logging
from flask_mail import Mail, Message

mail = Mail()
logger = logging.getLogger(__name__)


def init_mail(app):
    """Initialize Flask-Mail with the app."""
    mail.init_app(app)


def send_package_arrival(recipient_email, apartment, description):
    """Send email notifying resident that a package has arrived."""
    subject = f"📦 Nova encomenda para o apartamento {apartment}"
    body = (
        f"Olá, morador do apartamento {apartment}!\n\n"
        f"Uma nova encomenda chegou na portaria:\n"
        f"  Descrição: {description}\n\n"
        f"Acesse o sistema para confirmar a retirada digitalmente.\n\n"
        f"Atenciosamente,\n"
        f"Sistema de Encomendas do Condomínio"
    )
    _send_email(recipient_email, subject, body)


def send_pending_reminder(recipient_email, apartment, packages):
    """Send reminder email for pending packages."""
    package_list = "\n".join(
        f"  - {p['description']} (chegou em {p['arrival_date']}, {p['dias']} dias)"
        for p in packages
    )
    subject = f"⏰ Lembrete: encomenda(s) pendente(s) — Apto {apartment}"
    body = (
        f"Olá, morador do apartamento {apartment}!\n\n"
        f"Você possui encomenda(s) aguardando retirada na portaria:\n"
        f"{package_list}\n\n"
        f"Por favor, acesse o sistema para confirmar a retirada.\n\n"
        f"Atenciosamente,\n"
        f"Sistema de Encomendas do Condomínio"
    )
    _send_email(recipient_email, subject, body)


def _send_email(recipient, subject, body):
    """Send an email. Falls back to logging if SMTP is not configured."""
    try:
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        logger.info("E-mail enviado para %s: %s", recipient, subject)
    except Exception as e:
        # In POC mode without SMTP, log the email instead of failing
        logger.warning(
            "E-mail não enviado (SMTP não configurado). "
            "Destinatário: %s | Assunto: %s | Erro: %s",
            recipient, subject, e,
        )
