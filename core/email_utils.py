import httpx
from pydantic import EmailStr
from core.settings import settings

MAILERSEND_API_KEY = "mlsn.c0a6939af54393b1ff3abf452be3595ab9b641702dec73a147086549a569012f"  # Replace with env var if needed
MAILERSEND_API_URL = "https://api.mailersend.com/v1/email"
MAILERSEND_FROM = "onboarding@test-2p0347zmv23lzdrn.mlsender.net"  # must be a verified sender

async def send_verification_email(email: EmailStr, code: str):
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                MAILERSEND_API_URL,
                headers={
                    "Authorization": f"Bearer {MAILERSEND_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": {"email": MAILERSEND_FROM, "name": "Freshly"},
                    "to": [{"email": str(email), "name": str(email).split("@")[0]}],
                    "subject": "Your Freshly Verification Code",
                    "html": f"<p>Your verification code is: <strong>{code}</strong></p>"
                }
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print("MailerSend 422 error:", e.response.status_code, e.response.text)
            raise

async def send_password_reset_code(email: EmailStr, code: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            MAILERSEND_API_URL,
            headers={
                "Authorization": f"Bearer {MAILERSEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": {"email": MAILERSEND_FROM, "name": "Freshly"},
                "to": [{"email": str(email)}],
                "subject": "Your Freshly Password Reset Code",
                "html": f"<p>Use this code to reset your password: <strong>{code}</strong></p><p>It expires in 10 minutes.</p>"
            }
        )
        response.raise_for_status()