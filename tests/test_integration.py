from sqlalchemy import select

from app.config import settings
from app.models import LoginSession
from app.rate_limit import reset_rate_limits
from app.security import hash_token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_full_flow(client, user_data, sent_emails):
    assert client.post("/auth/register", json=user_data).status_code == 201
    login = client.post("/auth/login", json={"email": user_data["email"], "password": user_data["password"]})
    assert login.status_code == 200
    assert "access_token" not in login.json()  # el login solo NO da token
    code = sent_emails[-1][1]
    verify = client.post("/auth/verify-otp", json={"email": user_data["email"], "code": code})
    assert verify.status_code == 200
    profile = client.get("/users/profile", headers=_auth(verify.json()["access_token"]))
    assert profile.status_code == 200
    assert profile.json()["email"] == user_data["email"]


def test_register_duplicate_returns_409(client, registered_user):
    assert client.post("/auth/register", json=registered_user).status_code == 409


def test_login_wrong_password_returns_401(client, registered_user, sent_emails):
    r = client.post("/auth/login", json={"email": registered_user["email"], "password": "Incorrecta1"})
    assert r.status_code == 401
    assert sent_emails == []


def test_wrong_otp_returns_401(client, registered_user, sent_emails):
    client.post("/auth/login", json={"email": registered_user["email"], "password": registered_user["password"]})
    real = sent_emails[-1][1]
    wrong = "000000" if real != "000000" else "111111"
    r = client.post("/auth/verify-otp", json={"email": registered_user["email"], "code": wrong})
    assert r.status_code == 401


def test_protected_routes_need_token(client):
    assert client.get("/users/profile").status_code == 401
    assert client.get("/users/profile", headers=_auth("basura")).status_code == 401


def test_logout_revokes_token(client, auth_token):
    assert client.get("/users/profile", headers=_auth(auth_token)).status_code == 200
    assert client.post("/auth/logout", headers=_auth(auth_token)).status_code == 200
    assert client.get("/users/profile", headers=_auth(auth_token)).status_code == 401


def test_refresh_replaces_token(client, auth_token):
    r = client.post("/auth/refresh", headers=_auth(auth_token))
    assert r.status_code == 200
    new = r.json()["access_token"]
    assert client.get("/users/profile", headers=_auth(new)).status_code == 200
    assert client.get("/users/profile", headers=_auth(auth_token)).status_code == 401


def test_session_stores_hash_not_token(client, auth_token, db_session):
    session = db_session.scalars(select(LoginSession)).one()
    assert session.token != auth_token
    assert session.token == hash_token(auth_token)


def test_login_rate_limit_returns_429(client, registered_user, monkeypatch):
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    reset_rate_limits()
    body = {"email": registered_user["email"], "password": "Incorrecta1"}
    codes = [client.post("/auth/login", json=body).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429