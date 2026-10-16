import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import models  # noqa: F401  (registra las tablas)
from .database import Base, engine
from .routes import auth, users

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Al arrancar crea las tablas que no existan."""
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Sistema de Autenticación con OTP",
    description="Registro, login en dos pasos (contraseña + OTP por correo), JWT y logout con revocación.",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(users.router)


@app.get("/", tags=["Estado"])
def health():
    """Indica que el servicio está arriba."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, _exc: Exception):
    """Error 500 genérico: nunca se expone el detalle interno."""
    logger.exception("Error no controlado")
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})