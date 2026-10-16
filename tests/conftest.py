import os

# Deben definirse ANTES de importar la app
os.environ["SECRET_KEY"] = "clave-solo-para-tests-0123456789-abcdefghijklmnopqrstuvwxyz"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SMTP_USER"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["DEBUG_PRINT_OTP"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

import app.routes.auth as auth_routes  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.rate_limit import reset_rate_limits  # noqa: E402


@pytest.fixture(autouse=True)
def _rate_limit_off(monkeypatch):
    """Desactiva el rate limit en todos los tests (salvo el que lo prueba)."""
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", False)
    reset_rate_limits()
    yield
    reset_rate_limits()


@pytest.fixture()
def db_session():
    """BD SQLite en memoria, nueva en cada test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False)()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture()
def client(db_session):
    """Cliente HTTP conectado a la BD en memoria."""

    def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


@pytest.fixture()
def sent_emails(monkeypatch):
    """Intercepta los correos: cada elemento es (destinatario, código)."""
    box = []
    monkeypatch.setattr(auth_routes, "send_otp_email", lambda to, code: box.append((to, code)))
    return box


@pytest.fixture()
def user_data():
    return {"email": "ana@example.com", "password": "Clave12345", "full_name": "Ana Pérez"}


@pytest.fixture()
def registered_user(client, user_data):
    assert client.post("/auth/register", json=user_data).status_code == 201
    return user_data


@pytest.fixture()
def auth_token(client, registered_user, sent_emails):
    """Hace login + verify-otp y devuelve un JWT válido."""
    client.post("/auth/login", json={"email": registered_user["email"], "password": registered_user["password"]})
    code = sent_emails[-1][1]
    r = client.post("/auth/verify-otp", json={"email": registered_user["email"], "code": code})
    assert r.status_code == 200
    return r.json()["access_token"]