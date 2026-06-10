from urllib.parse import parse_qs, urlsplit

from app.db import session as db_session
from app.services.auth import create_password_reset_link, create_registration_link


def latest_email_token(email: str, purpose: str) -> str:
    with db_session.SessionLocal() as db:
        if purpose == "register":
            _response, link = create_registration_link(db, email)
        else:
            _response, link = create_password_reset_link(db, email)
        assert link is not None
        values = parse_qs(urlsplit(link).query)
        return values["token"][0]


def request_registration_token(client, email: str) -> str:
    response = client.post("/api/v1/auth/register/request", json={"email": email})
    assert response.status_code == 200, response.text
    return latest_email_token(email, "register")
