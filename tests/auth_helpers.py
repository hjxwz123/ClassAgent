from sqlalchemy import desc, select

from app.db.models import EmailCode
from app.db.session import SessionLocal


def latest_email_token(email: str, purpose: str) -> str:
    with SessionLocal() as db:
        record = db.scalars(
            select(EmailCode)
            .where(
                EmailCode.email == email,
                EmailCode.purpose == purpose,
            )
            .order_by(desc(EmailCode.id))
        ).first()
        assert record is not None
        return record.code


def request_registration_token(client, email: str) -> str:
    response = client.post("/api/v1/auth/register/request", json={"email": email})
    assert response.status_code == 200, response.text
    return latest_email_token(email, "register")
