import os
import smtplib
from email.message import EmailMessage
from app.core.config import settings


def send_reset_code_email(to_email: str, code: str) -> None:
    """
    Отправляет письмо с кодом для сброса пароля.
    Если SMTP не настроен — выводит код в консоль (для разработки).
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "465"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    mail_from = os.getenv("MAIL_FROM", smtp_user)
    mail_from_name = os.getenv("MAIL_FROM_NAME", "Smart ShopList")

    # Заглушка: если SMTP не настроен — печатаем код в консоль
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

    # Отправка через SMTP с SSL (порт 465) или STARTTLS (порт 587)
    if smtp_port == 465:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

    print(f"📧 Письмо с кодом отправлено на {to_email}")
