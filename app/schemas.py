from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    """Datos para registrar un usuario nuevo."""

    email: EmailStr = Field(..., examples=["ana@example.com"])
    password: str = Field(..., min_length=8, max_length=72, examples=["Clave12345"])
    full_name: str = Field(..., min_length=2, max_length=150, examples=["Ana Pérez"])

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, value: str) -> str:
        """Exige al menos una letra y un número, y máximo 72 bytes (límite de bcrypt)."""
        if not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
            raise ValueError("La contraseña debe contener al menos una letra y un número")
        if len(value.encode("utf-8")) > 72:
            raise ValueError("La contraseña es demasiado larga (máximo 72 bytes)")
        return value

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        """Quita espacios sobrantes y rechaza nombres vacíos."""
        value = value.strip()
        if len(value) < 2:
            raise ValueError("El nombre es demasiado corto")
        return value


class UserLogin(BaseModel):
    """Credenciales del primer factor."""

    email: EmailStr = Field(..., examples=["ana@example.com"])
    password: str = Field(..., min_length=1, max_length=72, examples=["Clave12345"])


class OTPVerify(BaseModel):
    """Verificación del código OTP (segundo factor)."""

    email: EmailStr = Field(..., examples=["ana@example.com"])
    code: str = Field(..., pattern=r"^\d{6}$", examples=["123456"])


class ResendOTP(BaseModel):
    """Solicitud para reenviar el código OTP."""

    email: EmailStr = Field(..., examples=["ana@example.com"])


class UserUpdate(BaseModel):
    """Campos del perfil que el usuario puede modificar."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=150, examples=["Ana María Pérez"])


class UserOut(BaseModel):
    """Datos públicos de un usuario (nunca incluye el hash de la contraseña)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., examples=[1])
    email: EmailStr = Field(..., examples=["ana@example.com"])
    full_name: str = Field(..., examples=["Ana Pérez"])
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    """Respuesta con el JWT de acceso."""

    access_token: str = Field(..., examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field("bearer", examples=["bearer"])
    expires_in: int = Field(..., description="Segundos hasta que expira el token", examples=[1800])


class MessageResponse(BaseModel):
    """Respuesta simple con un mensaje de texto."""

    message: str = Field(..., examples=["Operación exitosa"])