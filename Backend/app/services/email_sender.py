import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def send_email(*, to_email: str, subject: str, body: str) -> None:
    if not settings.smtp_user or not settings.smtp_password or not settings.smtp_from_email:
        raise RuntimeError(
            "SMTP is not configured. Set SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL in .env"
        )

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from_email
    message["To"] = to_email
    message.set_content(body)

    smtp_class = smtplib.SMTP_SSL if settings.smtp_port == 465 else smtplib.SMTP
    smtp_kwargs: dict = {"timeout": 15}
    if settings.smtp_port == 465:
        smtp_kwargs["context"] = ssl.create_default_context()

    with smtp_class(settings.smtp_host, settings.smtp_port, **smtp_kwargs) as smtp:
        smtp.ehlo()
        if settings.smtp_port != 465:
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        smtp.login(settings.smtp_user, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
