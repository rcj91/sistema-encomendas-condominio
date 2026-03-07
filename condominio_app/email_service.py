import logging
from flask_mail import Mail, Message

mail = Mail()
logger = logging.getLogger(__name__)


def init_mail(app):
    """Initialize Flask-Mail with the app."""
    mail.init_app(app)


def send_package_arrival(recipient_email, apartment, description, triggered_by="sistema"):
    """Send email notifying resident that a package has arrived."""
    subject = "Nova encomenda para o apartamento {}".format(apartment)
    body = (
        f"Olá, morador do apartamento {apartment}!\n\n"
        f"Uma nova encomenda chegou na portaria:\n"
        f"  Descrição: {description}\n\n"
        f"Acesse o sistema para confirmar a retirada digitalmente.\n\n"
        f"Atenciosamente,\n"
        f"Sistema de Encomendas do Condomínio"
    )
    _send_email(recipient_email, apartment, subject, body, triggered_by)


def send_pending_reminder(recipient_email, apartment, packages, triggered_by="sistema"):
    """Send reminder email for pending packages."""
    package_list = "\n".join(
        f"  - {p['description']} (chegou em {p['arrival_date']}, {p['dias']} dias)"
        for p in packages
    )
    subject = "Lembrete: encomenda(s) pendente(s) - Apto {}".format(apartment)
    body = (
        f"Olá, morador do apartamento {apartment}!\n\n"
        f"Você possui encomenda(s) aguardando retirada na portaria:\n"
        f"{package_list}\n\n"
        f"Por favor, acesse o sistema para confirmar a retirada.\n\n"
        f"Atenciosamente,\n"
        f"Sistema de Encomendas do Condomínio"
    )
    _send_email(recipient_email, apartment, subject, body, triggered_by)


def _send_email(recipient, apartment, subject, body, triggered_by="sistema"):
    """Send an email. Falls back to logging if SMTP is not configured."""
    from models import log_email
    status = "sent"
    try:
        msg = Message(subject=subject, recipients=[recipient], body=body)
        mail.send(msg)
        logger.info("E-mail enviado para %s: %s", recipient, subject)
    except Exception as e:
        status = "falha"
        logger.warning(
            "E-mail não enviado (SMTP não configurado). "
            "Destinatário: %s | Assunto: %s | Erro: %s",
            recipient, subject, e,
        )
    try:
        log_email(recipient, apartment, subject, body, triggered_by, status)
    except Exception:
        logger.warning("Falha ao gravar log de e-mail no banco.")
