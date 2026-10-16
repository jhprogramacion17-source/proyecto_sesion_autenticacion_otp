import os
from dotenv import load_dotenv

load_dotenv()  # carga las variables del archivo .env


class Settings:
    def __init__(self):
        self.SECRET_KEY = os.getenv("SECRET_KEY", "")
        if len(self.SECRET_KEY) < 32:
            raise RuntimeError("Define SECRET_KEY en el .env (mínimo 32 caracteres)")
        self.ALGORITHM = "HS256"
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.OTP_EXPIRE_MINUTES = min(int(os.getenv("OTP_EXPIRE_MINUTES", "15")), 15)
        self.DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./parcial_dos.db")
        self.SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USER = os.getenv("SMTP_USER", "")
        self.SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
        self.RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
        self.DEBUG_PRINT_OTP = os.getenv("DEBUG_PRINT_OTP", "false").lower() == "true"


settings = Settings()