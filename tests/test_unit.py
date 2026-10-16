from datetime import datetime, timedelta, timezone

import jwt
import pytest
from pydantic import ValidationError
from sqlalchemy import select

from app.config import settings
from app.models import OTPCode, User
from app.schemas import UserCreate
from app.security import create_access_token, decode_access_token, hash_password, verify_password
from app.services.otp_service import create_otp, generate_code, verify_otp
from app.utils import utcnow


def _make_user(db):
    user = User(email="u@example.com", password_hash=hash_password("Clave12345"), full_name="Usuario")
    db.add(user)
    db.commit()
    return user


def test_password_hash_and_verify():
    hashed = hash_password("Clave12345")
    assert hashed != "Clave12345"
    assert verify_password("Clave12345", hashed) is True
    assert verify_password("otra", hashed) is False


def test_password_hash_uses_random_salt():
    assert hash_password("Clave12345") != hash_password("Clave12345")


def test_generate_code_has_six_digits():
    for _ in range(100):
        code = generate_code()
        assert len(code) == 6 and code.isdigit()


def test_otp_is_valid_only_once(db_session):
    user = _make_user(db_session)
    code = create_otp(db_session, user.id)
    assert verify_otp(db_session, user.id, code) is True
    assert verify_otp(db_session, user.id, code) is False


def test_expired_otp_is_rejected(db_session):
    user = _make_user(db_session)
    code = create_otp(db_session, user.id)
    otp = db_session.scalars(select(OTPCode).where(OTPCode.user_id == user.id)).one()
    otp.expires_at = utcnow() - timedelta(minutes=1)
    db_session.commit()
    assert verify_otp(db_session, user.id, code) is False


def test_jwt_contains_exp_and_sub():
    token, _ = create_access_token(7)
    payload = decode_access_token(token)
    assert payload["sub"] == "7" and "exp" in payload


def test_expired_jwt_is_rejected():
    expired = jwt.encode(
        {"sub": "1", "jti": "x", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
        settings.SECRET_KEY, algorithm=settings.ALGORITHM,
    )
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(expired)


@pytest.mark.parametrize("password", ["corta1", "sololetras", "123456789"])
def test_weak_password_is_rejected(password):
    with pytest.raises(ValidationError):
        UserCreate(email="ana@example.com", password=password, full_name="Ana Pérez")