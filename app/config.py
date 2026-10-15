"""Configuración leída desde variables de entorno (sin secretos en el código)."""
import os
import secrets


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Config:
    APP_ENV = os.environ.get("APP_ENV", "development")
    DATABASE_PATH = os.environ.get("DATABASE_PATH", "instance/sgr.sqlite3")

    CODIGO_VIGENCIA_MIN = _int("CODIGO_VIGENCIA_MIN", 10)
    CODIGO_REENVIO_SEG = _int("CODIGO_REENVIO_SEG", 45)
    CODIGO_MAX_INTENTOS = _int("CODIGO_MAX_INTENTOS", 5)
    CODIGO_MAX_SOLICITUDES_HORA = _int("CODIGO_MAX_SOLICITUDES_HORA", 5)

    LOGIN_MAX_INTENTOS = _int("LOGIN_MAX_INTENTOS", 5)
    LOGIN_BLOQUEO_MIN = _int("LOGIN_BLOQUEO_MIN", 15)

    MAIL_MODE = os.environ.get("MAIL_MODE", "console")
    MAIL_FROM = os.environ.get("MAIL_FROM", "no-responder@example.test")
    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = _int("SMTP_PORT", 587)
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    DEV_OUTBOX = os.environ.get("DEV_OUTBOX", "1") == "1"

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    SESSION_MINUTES = _int("SESSION_MINUTES", 60)
    MAX_CONTENT_LENGTH = 1024 * 1024

    PAGE_SIZE_DEFAULT = 10
    PAGE_SIZE_MAX = 100

    @staticmethod
    def secret_key():
        key = os.environ.get("SECRET_KEY")
        if key:
            return key
        if os.environ.get("APP_ENV", "development") == "production":
            raise RuntimeError("SECRET_KEY es obligatoria en producción.")
        # Solo desarrollo: clave efímera (las sesiones se pierden al reiniciar).
        return secrets.token_hex(32)
