import logging
import smtplib
from email.message import EmailMessage

from ..config import settings

logger = logging.getLogger(__name__)


def send_otp_email(to: str, code: str) -> None:
    """Envía el OTP por correo (smtplib). Nunca lanza errores hacia el cliente."""
    if settings.DEBUG_PRINT_OTP:  # solo desarrollo: ver el código en la terminal
        print(f"[DEV] Código OTP para {to}: {code}")

    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning("SMTP no configurado: no se envió el correo.")
        return

    message = EmailMessage()
    message["Subject"] = "Tu código de verificación"
    message["From"] = settings.SMTP_USER
    message["To"] = to
    message.set_content(
        f"Tu código de verificación es: {code}\n\n"
        f"Expira en {settings.OTP_EXPIRE_MINUTES} minutos. "
        "Si no fuiste tú, ignora este mensaje."
    )

    try:
        use_ssl = settings.SMTP_PORT == 465
        smtp_class = smtplib.SMTP_SSL if use_ssl else smtplib.SMTP
        with smtp_class(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if not use_ssl:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
    except Exception:
        # No se registra el código, ni la clave, ni el correo del usuario
        logger.error("Falló el envío del correo OTP (revisa la configuración SMTP).")