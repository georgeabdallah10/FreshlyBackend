from core.settings import settings
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
import ssl, certifi

tls_context = ssl.create_default_context(cafile=certifi.where())

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,   # 587
    MAIL_SERVER=settings.MAIL_SERVER,  # smtp.gmail.com
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

async def send_verification_email(email: EmailStr, code: str):
    message = MessageSchema(
        subject="Your Freshly Verification Code",
        recipients=[email],
        body=f"Your verification code is: {code}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_password_reset_code(email: EmailStr, code: str):
    message = MessageSchema(
        subject="Your Freshly Password Reset Code",
        recipients=[email],
        body=f"Use this code to reset your password: {code}\n\nIt expires in 10 minutes.",
        subtype="plain",
    )
    await FastMail(conf).send_message(message)