from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..middleware import AuthContext, get_auth_context
from ..models import LoginSession, User
from ..rate_limit import rate_limit
from ..schemas import MessageResponse, OTPVerify, ResendOTP, Token, UserCreate, UserLogin, UserOut
from ..security import DUMMY_HASH, create_access_token, hash_password, hash_token, verify_password
from ..services.email_service import send_otp_email
from ..services.otp_service import create_otp, verify_otp
from ..utils import utcnow

router = APIRouter(prefix="/auth", tags=["Autenticación"])

OTP_MESSAGE = f"Si los datos son correctos, enviamos un código OTP a tu correo (válido {settings.OTP_EXPIRE_MINUTES} minutos)."


def _get_user(db: Session, email: str):
    """Busca un usuario por correo (en minúsculas)."""
    return db.scalar(select(User).where(User.email == email.lower()))


def _create_session(db: Session, user_id: int) -> Token:
    """Crea el JWT y guarda su sesión (solo el hash del token) en login_sessions."""
    token, expires_at = create_access_token(user_id)
    db.add(LoginSession(user_id=user_id, token=hash_token(token), expires_at=expires_at))
    db.commit()
    return Token(access_token=token, token_type="bearer", expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(rate_limit("register", 10, 60))])
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Registra un usuario. La contraseña se guarda con hash bcrypt."""
    if _get_user(db, data.email):
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    user = User(email=data.email.lower(), password_hash=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "El correo ya está registrado")
    db.refresh(user)
    return user


@router.post("/login", response_model=MessageResponse,
             dependencies=[Depends(rate_limit("login", 5, 60))])
def login(data: UserLogin, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Paso 1: valida email y contraseña, genera el OTP y lo envía. Aún no entrega token."""
    user = _get_user(db, data.email)
    password_ok = verify_password(data.password, user.password_hash if user else DUMMY_HASH)
    if user is None or not password_ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales inválidas")
    code = create_otp(db, user.id)
    background_tasks.add_task(send_otp_email, user.email, code)
    return MessageResponse(message=OTP_MESSAGE)


@router.post("/verify-otp", response_model=Token,
             dependencies=[Depends(rate_limit("verify-otp", 5, 60))])
def verify_otp_code(data: OTPVerify, db: Session = Depends(get_db)):
    """Paso 2: valida el OTP y entrega el JWT."""
    user = _get_user(db, data.email)
    if user is None or not verify_otp(db, user.id, data.code):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Código OTP inválido o expirado")
    # limpieza: borrar sesiones vencidas de este usuario
    db.execute(delete(LoginSession).where(LoginSession.user_id == user.id, LoginSession.expires_at <= utcnow()))
    return _create_session(db, user.id)


@router.post("/resend-otp", response_model=MessageResponse,
             dependencies=[Depends(rate_limit("resend-otp", 3, 60))])
def resend_otp(data: ResendOTP, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Reenvía un OTP nuevo. Responde igual exista o no el correo (no revela usuarios)."""
    user = _get_user(db, data.email)
    if user is not None:
        code = create_otp(db, user.id)
        background_tasks.add_task(send_otp_email, user.email, code)
    return MessageResponse(message=OTP_MESSAGE)


@router.post("/refresh", response_model=Token,
             dependencies=[Depends(rate_limit("refresh", 10, 60))])
def refresh(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """Emite un token nuevo y revoca el anterior."""
    db.delete(context.session)
    return _create_session(db, context.user.id)


@router.post("/logout", response_model=MessageResponse)
def logout(context: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    """Borra la sesión: el token queda revocado al instante."""
    db.delete(context.session)
    db.commit()
    return MessageResponse(message="Sesión cerrada correctamente")