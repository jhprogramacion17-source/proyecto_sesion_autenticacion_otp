from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import LoginSession, User
from .security import decode_access_token, hash_token
from .utils import utcnow

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthContext:
    """Usuario y sesión de la petición autenticada."""

    user: User
    session: LoginSession


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_auth_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Valida el token: firma + expiración + sesión activa en la BD + usuario existente."""
    if credentials is None:
        raise _unauthorized("No autenticado")

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        raise _unauthorized("Token inválido o expirado")

    session = db.scalars(select(LoginSession).where(LoginSession.token == hash_token(token))).first()
    if session is None:
        raise _unauthorized("Sesión inválida o revocada")
    if session.expires_at <= utcnow():
        db.delete(session)
        db.commit()
        raise _unauthorized("Sesión expirada")

    user = db.get(User, session.user_id)
    if user is None or str(user.id) != payload["sub"]:
        raise _unauthorized("Sesión inválida o revocada")

    return AuthContext(user=user, session=session)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    """Dependencia corta que devuelve solo el usuario autenticado."""
    return context.user