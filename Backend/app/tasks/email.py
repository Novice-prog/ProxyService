from app.core.celery_app import celery_app
from app.services.email_sender import send_email

@celery_app.task(
    name = "email.send_activation_key",
    bind = True,
    autoretry_for = (Exception,),
    retry_backoff = True,
    retry_backoff_max = 300,
    retry_jitter = True,
    max_retries = 5,
)
def send_activation_key(
    self, 
    *, 
    email: str,
    activation_key: str,
)-> None:
    
    send_email(
        to_email=email,
        subject="Ваш ключ активации",
        body = (
            "Здравствуйте!\n\n"
            "Ваш ключ активации:\n\n"
            f"{activation_key}\n\n"
            "Вставьте этот ключ в десктопное приложение для подключения к прокси.\n"
        )
    )