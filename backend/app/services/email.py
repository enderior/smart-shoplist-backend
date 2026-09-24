import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_reset_code_email(to_email: str, code: str) -> None:
    """Отправляет код на email. Если SMTP не настроен — пишет в консоль.
    Ошибки SMTP логируются, но не пробрасываются."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", smtp_user)
    mail_from_name = os.getenv("MAIL_FROM_NAME", "Smart ShopList")

    if not smtp_host or not smtp_user or not smtp_password:
        print(f"📧 [DEV] Код для сброса пароля для {to_email}: {code}")
        return

    msg = EmailMessage()
    msg["Subject"] = "Сброс пароля — Smart ShopList"
    msg["From"] = f"{mail_from_name} <{mail_from}>"
    msg["To"] = to_email
    msg.set_content(
        f"Ваш код для сброса пароля: {code}\n\n"
        f"Код действует 15 минут. Если вы не запрашивали сброс — просто проигнорируйте письмо."
    )

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
        print(f"📧 Письмо с кодом отправлено на {to_email}")
    except Exception as e:
        logger.error(f"Не удалось отправить письмо на {to_email}: {e}")
        print(f"📧 [DEV-FALLBACK] Код для сброса пароля для {to_email}: {code}")
