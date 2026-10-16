import hashlib
import hmac
import secrets
from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import settings
from ..models import OTPCode
from ..utils import utcnow


def _digest(code: str) -> str:
    """HMAC-SHA256 del código: en la BD nunca se guarda el código en claro."""
    return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()


def generate_code() -> str:
    """Código aleatorio seguro de 6 dígitos (con ceros a la izquierda si hace falta)."""
    return f"{secrets.randbelow(1_000_000):06d}"


def create_otp(db: Session, user_id: int) -> str:
    """Crea un OTP nuevo, invalida los anteriores y devuelve el código en claro (para el correo)."""
    db.execute(
        update(OTPCode).where(OTPCode.user_id == user_id, OTPCode.used.is_(False)).values(used=True)
    )
    code = generate_code()
    db.add(
        OTPCode(
            user_id=user_id,
            code=_digest(code),
            expires_at=utcnow() + timedelta(minutes=settings.OTP_EXPIRE_MINUTES),
            used=False,
        )
    )
    db.commit()
    return code


def verify_otp(db: Session, user_id: int, code: str) -> bool:
    """True si el OTP existe, no está usado y no ha vencido. Lo marca como usado."""
    otp = db.scalars(
        select(OTPCode).where(
            OTPCode.user_id == user_id,
            OTPCode.code == _digest(code),
            OTPCode.used.is_(False),
        )
    ).first()
    if otp is None or otp.expires_at <= utcnow():
        return False
    otp.used = True
    db.commit()
    return True