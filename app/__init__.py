"""Fábrica de la aplicación SGR (Municipalidad de La Serena)."""
import os

from flask import Flask, g, jsonify, render_template, request

from .config import Config
from .db import close_db
from .engine import ErrorNegocio, manejar_error_negocio, registrar_recurso
from .permisos import MODULOS
from .security import antes_de_solicitud, error_json, es_api, tiene, token_csrf


def create_app(overrides=None):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    app.config["SECRET_KEY"] = Config.secret_key()
    app.config["PERMANENT_SESSION_LIFETIME"] = Config.SESSION_MINUTES * 60
    if not os.path.isabs(app.config["DATABASE_PATH"]) and app.config["DATABASE_PATH"] != ":memory:":
        app.config["DATABASE_PATH"] = os.path.join(base, app.config["DATABASE_PATH"])
    try:
        with open(os.path.join(base, "VERSION"), encoding="utf-8") as fh:
            app.config["APP_VERSION"] = fh.read().strip()
    except OSError:
        app.config["APP_VERSION"] = "desconocida"
    app.config["GIT_COMMIT"] = os.environ.get("GIT_COMMIT", "")[:12]
    if overrides:
        app.config.update(overrides)

    app.teardown_appcontext(close_db)
    app.before_request(antes_de_solicitud)

    from . import routes_auth, routes_main
    from .resources import RECURSOS
    app.register_blueprint(routes_auth.bp)
    app.register_blueprint(routes_main.bp)
    for r in RECURSOS:
        registrar_recurso(app, r)
    routes_main._registrar_paginas_crud(app)
    routes_main._registrar_paginas_pendientes(app)

    app.register_error_handler(ErrorNegocio, manejar_error_negocio)

    @app.errorhandler(404)
    def _404(_e):
        if es_api():
            return error_json(404, "no_encontrado", "El recurso solicitado no existe.")
        return render_template("error.html", codigo=404, titulo="Página no encontrada",
                               detalle="La dirección no existe o fue movida."), 404

    @app.errorhandler(405)
    def _405(_e):
        return error_json(405, "metodo", "Método no permitido.") if es_api() else (
            render_template("error.html", codigo=405, titulo="Acción no permitida", detalle=""), 405)

    @app.errorhandler(413)
    def _413(_e):
        return error_json(413, "demasiado_grande", "La solicitud supera el tamaño permitido.")

    @app.errorhandler(500)
    def _500(_e):
        if es_api():
            return error_json(500, "error_servidor", "Ocurrió un error inesperado. Inténtalo nuevamente en unos minutos.")
        return render_template("error.html", codigo=500, titulo="Error del servidor",
                               detalle="Ocurrió un error inesperado. Inténtalo nuevamente en unos minutos."), 500

    @app.after_request
    def _cabeceras(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        resp.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self' https://cdn.jsdelivr.net 'unsafe-inline'; img-src 'self' data:; "
            "font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
        if request.endpoint != "static" and (es_api() or g.get("user")):
            resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.context_processor
    def _contexto():
        menu = []
        if g.get("user"):
            for clave, etiqueta, _acc, ruta, operativo in MODULOS:
                if tiene(f"{clave}:ver") or clave == "inicio":
                    menu.append({"clave": clave, "t": etiqueta, "ruta": ruta, "operativo": operativo})
        return {"csrf_token": token_csrf(), "menu": menu, "app_version": app.config["APP_VERSION"],
                "git_commit": app.config["GIT_COMMIT"], "vigencia_min": app.config["CODIGO_VIGENCIA_MIN"]}

    return app
