#!/usr/bin/env python3
"""Utilidades de línea de comandos.

  python manage.py init-db --demo            Crea la BD con roles, delegaciones y cuentas demo
  python manage.py init-db --demo --volumen 5000   Además genera 5000 atenciones ficticias
  python manage.py init-db                   Solo roles y delegaciones base (sin usuarios)
  python manage.py crear-superadmin          Crea un superadministrador (pide la clave por teclado)
  python manage.py run                       Servidor de desarrollo (no usar en producción)
"""
import argparse
import getpass
import os
import sys

from app import create_app
from app.config import Config
from app.db import _connect, init_db
from app.security import hashear
from app.validators import EMAIL_RE, validar_password


def _ruta_bd():
    ruta = Config.DATABASE_PATH
    return ruta if os.path.isabs(ruta) else os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init-db")
    i.add_argument("--demo", action="store_true")
    i.add_argument("--volumen", type=int, default=0)
    sub.add_parser("crear-superadmin")
    sub.add_parser("run")
    a = p.parse_args()

    if a.cmd == "init-db":
        init_db(_ruta_bd(), demo=a.demo, volumen=a.volumen)
        print("Base de datos lista:", _ruta_bd())
    elif a.cmd == "crear-superadmin":
        init_db(_ruta_bd(), demo=False)
        usuario = input("Usuario: ").strip().lower()
        correo = input("Correo: ").strip().lower()
        if not EMAIL_RE.match(correo):
            sys.exit("Correo inválido.")
        clave = getpass.getpass("Contraseña: ")
        err = validar_password(clave, contexto=(usuario,))
        if err:
            sys.exit(err)
        conn = _connect(_ruta_bd())
        rol = conn.execute("SELECT id FROM roles WHERE codigo='ROL01'").fetchone()[0]
        dele = conn.execute("SELECT id FROM delegaciones ORDER BY codigo LIMIT 1").fetchone()[0]
        cur = conn.execute("INSERT INTO usuarios (usuario,nombre,correo,password_hash,rol_id,ultima_delegacion_id) VALUES (?,?,?,?,?,?)",
                           (usuario, usuario, correo, hashear(clave), rol, dele))
        conn.execute("INSERT INTO usuario_delegacion VALUES (?,?)", (cur.lastrowid, dele))
        conn.commit()
        print("Superadministrador creado.")
    elif a.cmd == "run":
        create_app().run(debug=os.environ.get("APP_ENV") != "production", port=int(os.environ.get("PORT", 5000)))


if __name__ == "__main__":
    main()
