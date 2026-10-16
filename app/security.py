import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Tuple

import bcrypt
import jwt

from .config import settings
from .utils import utcnow


def hash_password(password: str) -> str:
    """Hash bcrypt (con sal aleatoria) de una contraseña."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Compara una contraseña contra su hash bcrypt."""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


# Hash de relleno: el login tarda igual si el correo no existe (evita enumerar usuarios por tiempos)
DUMMY_HASH = hash_password("contraseña-de-relleno-no-usar")


def create_access_token(user_id: int) -> Tuple[str, datetime]:
    """Crea un JWT firmado con los claims sub, jti y exp. Devuelve (token, expires_at)."""
    expires_at = utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "jti": uuid.uuid4().hex,  # id único: dos tokens nunca son iguales
        "exp": expires_at.replace(tzinfo=timezone.utc),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Valida firma y expiración. Lanza jwt.PyJWTError si el token no es válido."""
    return jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[settings.ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )


def hash_token(token: str) -> str:
    """SHA-256 del token: en la BD se guarda este hash, no el JWT."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()