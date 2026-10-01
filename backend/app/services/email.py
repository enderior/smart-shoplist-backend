import os
import logging
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


def send_code_email(to_email: str, code: str, subject: str, intro: str) -> None:
    """
    Универсальная отправка кода по email.
    Если SMTP не настроен — печатает в консоль (dev-режим).
    Ошибки SMTP логируются, но не пробрасываются.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", smtp_user)
    mail_from_name = os.getenv("MAIL_FROM_NAME", "Smart ShopList")

    if not smtp_host or not smtp_user or not smtp_password:
        print(f"📧 [DEV] {subject} для {to_email}: {code}")
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{mail_from_name} <{mail_from}>"
    msg["To"] = to_email
    msg.set_content(
        f"{intro}: {code}\n\n"
        f"Код действует 15 минут. Если вы не запрашивали это — просто проигнорируйте письмо."
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
        print(f"📧 Письмо отправлено на {to_email}")
    except Exception as e:
        logger.error(f"Не удалось отправить письмо на {to_email}: {e}")
        print(f"📧 [DEV-FALLBACK] {subject} для {to_email}: {code}")


# ========== Обёртки для конкретных сценариев ==========

def send_reset_code_email(to_email: str, code: str) -> None:
    send_code_email(
        to_email=to_email,
        code=code,
        subject="Сброс пароля — Smart ShopList",
        intro="Ваш код для сброса пароля",
    )


def send_email_change_code_email(to_new_email: str, code: str) -> None:
    send_code_email(
        to_email=to_new_email,
        code=code,
        subject="Подтверждение нового email — Smart ShopList",
        intro="Ваш код для подтверждения нового email",
    )


def send_phone_change_code_email(to_email: str, code: str) -> None:
    send_code_email(
        to_email=to_email,
        code=code,
        subject="Подтверждение нового телефона — Smart ShopList",
        intro="Ваш код для подтверждения нового телефона",
    )
