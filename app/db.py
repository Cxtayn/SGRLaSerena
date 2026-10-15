"""Acceso a SQLite: una conexión por solicitud, claves foráneas activas y
normalización de texto (minúsculas y sin tildes) para el buscador."""
import os
import sqlite3
import unicodedata
from datetime import datetime, timezone

from flask import current_app, g


def normalizar(texto):
    """Minúsculas y sin tildes: 'Educación' -> 'educacion'."""
    if texto is None:
        return ""
    texto = unicodedata.normalize("NFD", str(texto))
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    return texto.casefold()


def ahora_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _connect(path):
    if path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 15000")
    conn.create_function("norm", 1, normalizar, deterministic=True)
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE_PATH"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db(path, demo=True, volumen=0):
    """Crea el esquema y los datos base. ``demo`` agrega usuarios de prueba; ``volumen``
    agrega N atenciones ficticias para probar paginación y carga."""
    conn = _connect(path)
    schema = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "schema.sql")
    with open(schema, encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.commit()
    from .seed import cargar_semilla
    cargar_semilla(conn, demo=demo, volumen=volumen)
    conn.close()
