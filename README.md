# Sistema de Autenticación con OTP — FastAPI

API REST de autenticación en dos factores: contraseña + código OTP de 6 dígitos enviado por correo (válido 15 minutos). Entrega tokens JWT con expiración, protege rutas y permite cerrar sesión revocando el token.

**Stack:** FastAPI · SQLAlchemy · SQLite · Pydantic · bcrypt · PyJWT · smtplib · pytest

**URL del despliegue:** https://TU_USUARIO.pythonanywhere.com/docs

## Flujo

```
POST /auth/register    -> crea el usuario (contraseña con hash bcrypt)
POST /auth/login       -> valida correo + contraseña, genera el OTP y lo envía (aún sin token)
POST /auth/verify-otp  -> valida el OTP y entrega el JWT
GET  /users/profile    -> ruta protegida (Authorization: Bearer <token>)
POST /auth/logout      -> borra la sesión: el token queda revocado
```

Un token solo es válido si su firma y su `exp` son correctos **y** existe su sesión en la tabla `login_sessions`. Por eso el logout revoca el token de verdad.

## Estructura

```
app/
├── main.py            aplicación, routers y manejo global de errores
├── config.py          variables de entorno
├── database.py        engine y sesión de SQLAlchemy
├── models.py          tablas: users, otp_codes, login_sessions
├── schemas.py         esquemas Pydantic con ejemplos
├── security.py        hash bcrypt y JWT
├── middleware.py      validación del token
├── rate_limit.py      límite de peticiones por IP
├── utils.py           utilidades de fecha (UTC)
├── routes/
│   ├── auth.py        endpoints /auth/*
│   └── users.py       endpoints /users/*
└── services/
    ├── otp_service.py   generación y validación del OTP
    └── email_service.py envío por SMTP
tests/                 tests unitarios y de integración (pytest)
```

## Instalación local (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Crea el archivo `.env` en la raíz del proyecto (ver la tabla de variables más abajo) y arranca:

```powershell
uvicorn app.main:app --reload
```

Abre http://127.0.0.1:8000/docs para probar los endpoints. Las tablas se crean solas al arrancar.

En Linux/macOS, activa el entorno con `source venv/bin/activate`.

## Variables de entorno (`.env`)

| Variable | Descripción | Por defecto |
|---|---|---|
| `SECRET_KEY` | Llave para firmar los JWT (mínimo 32 caracteres). **Obligatoria** | — |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del JWT | 30 |
| `OTP_EXPIRE_MINUTES` | Duración del OTP (máximo 15) | 15 |
| `DATABASE_URL` | URL de la base de datos | `sqlite:///./parcial_dos.db` |
| `SMTP_HOST` / `SMTP_PORT` | Servidor de correo | `smtp.gmail.com` / `587` |
| `SMTP_USER` | Correo remitente | — |
| `SMTP_PASSWORD` | Contraseña de aplicación de Google (16 letras, sin espacios) | — |
| `RATE_LIMIT_ENABLED` | Activa el límite de peticiones | `true` |
| `DEBUG_PRINT_OTP` | Imprime el OTP en consola (**solo desarrollo**) | `false` |

Genera la `SECRET_KEY` con:
```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

**Gmail:** activa la verificación en 2 pasos y crea una contraseña de aplicación en https://myaccount.google.com/apppasswords. La contraseña normal no funciona. El archivo `.env` nunca se sube a Git.

## Endpoints

| Método | Ruta | Descripción | Auth | Límite |
|---|---|---|---|---|
| POST | `/auth/register` | Registrar usuario | No | 10/min |
| POST | `/auth/login` | Validar credenciales y enviar OTP | No | 5/min |
| POST | `/auth/verify-otp` | Verificar OTP y obtener JWT | No | 5/min |
| POST | `/auth/resend-otp` | Reenviar OTP | No | 3/min |
| POST | `/auth/refresh` | Emitir token nuevo (revoca el anterior) | Sí | 10/min |
| POST | `/auth/logout` | Cerrar sesión y revocar el token | Sí | — |
| GET | `/users/profile` | Ver perfil | Sí | — |
| PUT | `/users/profile` | Actualizar perfil | Sí | — |

**Códigos de respuesta:** `200` ok · `201` creado · `401` no autenticado, credenciales u OTP inválidos · `409` correo ya registrado · `422` datos inválidos · `429` demasiadas solicitudes · `500` error interno (mensaje genérico).

## Base de datos

| Tabla | Campos |
|---|---|
| `users` | id, email (único), password_hash, full_name, created_at, updated_at |
| `otp_codes` | id, user_id (FK), code, expires_at, used, created_at |
| `login_sessions` | id, user_id (FK), token, expires_at, created_at |

`password_hash` guarda el hash bcrypt; `otp_codes.code` guarda un HMAC-SHA256 del código; `login_sessions.token` guarda el SHA-256 del JWT. Nunca se guardan contraseñas, códigos ni tokens en claro.

## Tests

```bash
pytest -v
```

19 tests (10 unitarios y 9 de integración). Usan una base de datos SQLite en memoria y simulan el envío de correos; no tocan `parcial_dos.db`.

## Seguridad

- **Contraseñas:** hash bcrypt con sal aleatoria; mínimo 8 caracteres con letras y números.
- **JWT:** firmado con HS256, con claims `sub`, `jti` y `exp`.
- **Revocación:** cada sesión se guarda en `login_sessions`; el logout la borra y el token deja de servir.
- **OTP:** 6 dígitos generados con `secrets`, vigencia máxima de 15 minutos, un solo uso; uno nuevo invalida los anteriores.
- **Sin enumeración de usuarios:** mensajes de error genéricos y `resend-otp` responde igual exista o no el correo.
- **Rate limiting** por IP en los endpoints críticos.
- **Errores y logs:** los errores internos devuelven un mensaje genérico; no se registran contraseñas, tokens ni OTP.
- **Secretos** solo en variables de entorno; `.env` está en `.gitignore`.

## Limitaciones conocidas

- El rate limiting es en memoria y por proceso (se reinicia con el servidor); en producción se usaría Redis.
- No hay límite de intentos fallidos de OTP por cuenta, solo por IP.
- Cada petición protegida consulta la base de datos para validar la sesión; es el costo de poder revocar tokens al instante.
- SQLite es suficiente para este proyecto; para más carga se migraría a PostgreSQL o MySQL cambiando `DATABASE_URL`.

