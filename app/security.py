"""Sesión, CSRF, permisos y alcance por delegación. Todo se valida en el servidor:
ocultar botones en la interfaz NO es control de acceso."""
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import current_app, g, jsonify, redirect, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

RUTAS_PUBLICAS = {
    "static", "auth.login_page", "auth.api_login", "auth.recuperar_page", "auth.validar_page",
    "auth.nueva_page", "auth.api_rec_solicitar", "auth.api_rec_validar", "auth.api_rec_reenviar",
    "auth.api_rec_nueva", "main.salud", "main.dev_bandeja",
}
METODOS_ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}


# ---------------------------------------------------------------- utilidades
def hashear(password):
    return generate_password_hash(password)


def verificar_hash(hash_guardado, password):
    return check_password_hash(hash_guardado, password)


def firmar_codigo(codigo):
    """Hash con sal global para códigos de 6 dígitos (no se guardan en claro)."""
    import hashlib
    clave = current_app.config["SECRET_KEY"].encode()
    return hmac.new(clave, str(codigo).encode(), hashlib.sha256).hexdigest()


def error_json(status, codigo, mensaje, campos=None, **extra):
    cuerpo = {"ok": False, "error": codigo, "mensaje": mensaje}
    if campos:
        cuerpo["campos"] = campos
    cuerpo.update(extra)
    resp = jsonify(cuerpo)
    resp.status_code = status
    return resp


def es_api():
    return request.path.startswith("/api/")


# --------------------------------------------------------------------- CSRF
def token_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


def verificar_csrf():
    if request.method not in METODOS_ESCRITURA:
        return None
    enviado = request.headers.get("X-CSRF-Token", "")
    esperado = session.get("csrf", "")
    if not esperado or not hmac.compare_digest(enviado, esperado):
        return error_json(403, "csrf", "La sesión de seguridad expiró. Recarga la página e inténtalo de nuevo.")
    return None


# ------------------------------------------------------------- contexto/usuario
def delegaciones_autorizadas(db, usuario_id, alcance):
    if alcance == "TODAS":
        filas = db.execute("SELECT id, codigo, nombre FROM delegaciones WHERE activo=1 ORDER BY codigo").fetchall()
    else:
        filas = db.execute(
            "SELECT d.id, d.codigo, d.nombre FROM delegaciones d "
            "JOIN usuario_delegacion ud ON ud.delegacion_id=d.id "
            "WHERE ud.usuario_id=? AND d.activo=1 ORDER BY d.codigo", (usuario_id,)).fetchall()
    return [dict(f) for f in filas]


def cargar_contexto():
    """before_request: resuelve usuario, rol, permisos y delegación activa desde la BD
    en cada solicitud, de modo que desactivar una cuenta o cambiar un rol surte efecto
    de inmediato."""
    g.user = None
    g.permisos = frozenset()
    g.delegaciones = []
    g.delegacion = None
    uid = session.get("uid")
    if not uid:
        return
    db = get_db()
    fila = db.execute(
        "SELECT u.*, r.nombre AS rol_nombre, r.codigo AS rol_codigo, r.alcance AS alcance, "
        "r.permisos AS rol_permisos, r.activo AS rol_activo "
        "FROM usuarios u JOIN roles r ON r.id=u.rol_id WHERE u.id=?", (uid,)).fetchone()
    if (not fila or not fila["activo"] or not fila["rol_activo"]
            or fila["session_version"] != session.get("sv")):
        session.clear()
        return
    deleg = delegaciones_autorizadas(db, fila["id"], fila["alcance"])
    if not deleg:
        session.clear()
        return
    ids = {d["id"] for d in deleg}
    elegida = session.get("deleg")
    if elegida not in ids:
        elegida = fila["ultima_delegacion_id"] if fila["ultima_delegacion_id"] in ids else deleg[0]["id"]
        session["deleg"] = elegida
    g.user = dict(fila)
    g.permisos = frozenset(json.loads(fila["rol_permisos"] or "[]"))
    g.delegaciones = deleg
    g.delegacion = next(d for d in deleg if d["id"] == elegida)
    session.permanent = True


def antes_de_solicitud():
    # CSRF primero: también protege login y recuperación.
    if request.endpoint and request.endpoint != "static":
        token_csrf()
        falla = verificar_csrf()
        if falla is not None:
            return falla
    cargar_contexto()
    if request.endpoint in RUTAS_PUBLICAS or request.endpoint is None:
        return None
    if g.user is None:
        if es_api():
            return error_json(401, "no_autenticado", "Tu sesión no está activa. Inicia sesión nuevamente.")
        return redirect(url_for("auth.login_page", next=request.full_path.rstrip("?")))
    return None


def requiere(permiso):
    """Decorador: exige un permiso del rol. Se valida SIEMPRE en el servidor."""
    def deco(fn):
        @wraps(fn)
        def interior(*a, **kw):
            if permiso not in g.permisos:
                if es_api():
                    return error_json(403, "sin_permiso", "Tu perfil no tiene permiso para esta acción.")
                from flask import render_template
                return render_template("error.html", codigo=403, titulo="Acceso no autorizado",
                                       detalle="Tu perfil no incluye este módulo."), 403
            return fn(*a, **kw)
        return interior
    return deco


def tiene(permiso):
    return permiso in g.permisos


def ids_delegaciones_autorizadas():
    return [d["id"] for d in g.delegaciones]


def es_alcance_total():
    return bool(g.user) and g.user["alcance"] == "TODAS"


# ------------------------------------------------------- intentos de login
def _ahora():
    return datetime.now(timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def segundos_bloqueo_login(identificador):
    """Segundos restantes de bloqueo para un identificador (0 si no está bloqueado).
    Se calcula igual exista o no la cuenta, para no revelar cuentas."""
    cfg = current_app.config
    db = get_db()
    desde = _iso(_ahora() - timedelta(minutes=cfg["LOGIN_BLOQUEO_MIN"]))
    filas = db.execute(
        "SELECT creado_en FROM intentos_login WHERE identificador=? AND creado_en>=? ORDER BY creado_en DESC",
        (identificador, desde)).fetchall()
    if len(filas) < cfg["LOGIN_MAX_INTENTOS"]:
        return 0
    ref = datetime.strptime(filas[cfg["LOGIN_MAX_INTENTOS"] - 1]["creado_en"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    restante = (ref + timedelta(minutes=cfg["LOGIN_BLOQUEO_MIN"]) - _ahora()).total_seconds()
    return max(0, int(restante) + 1)


def registrar_intento_fallido(identificador):
    db = get_db()
    db.execute("INSERT INTO intentos_login (identificador, creado_en) VALUES (?,?)", (identificador, _iso(_ahora())))
    db.commit()


def limpiar_intentos(identificador):
    db = get_db()
    db.execute("DELETE FROM intentos_login WHERE identificador=?", (identificador,))
    db.commit()
