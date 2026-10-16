from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String

from .database import Base
from .utils import utcnow


class User(Base):
    """Usuario registrado en el sistema."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # hash bcrypt, nunca la contraseña
    full_name = Column(String(150), nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow, nullable=False)


class OTPCode(Base):
    """Código OTP de un solo uso, con vencimiento."""

    __tablename__ = "otp_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    code = Column(String(64), nullable=False)  # se guarda un hash del código, no el código
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class LoginSession(Base):
    """Sesión activa. Si la fila no existe, el token queda revocado."""

    __tablename__ = "login_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(64), unique=True, index=True, nullable=False)  # hash SHA-256 del JWT
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=utcnow, nullable=False)