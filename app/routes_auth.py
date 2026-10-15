"""Login, cierre de sesión y recuperación de contraseña (3 pasos)."""
import secrets
import time
from datetime import datetime, timedelta, timezone

from flask import (Blueprint, current_app, g, jsonify, redirect, render_template, request, session,
                   url_for)

from .db import ahora_iso, get_db, normalizar
from .mailer import enviar_correo
from .security import (error_json, firmar_codigo, hashear, limpiar_intentos, registrar_intento_fallido,
                       segundos_bloqueo_login, token_csrf, verificar_hash)
from .validators import (EMAIL_RE, PASSWORD_REQUISITOS, enmascarar_correo, limpiar_texto, validar_password)

bp = Blueprint("auth", __name__)

MSJ_GENERICO_RECUPERAR = "Si la cuenta existe, recibirás instrucciones en tu correo."
MSJ_LOGIN_INVALIDO = "Usuario o contraseña incorrectos. Revisa los datos e inténtalo nuevamente."
# Hash de relleno: iguala el tiempo de respuesta cuando el usuario no existe.
_HASH_RELLENO = hashear("relleno-no-valido-1A!")


def _dt(iso):
    return datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _ahora():
    return datetime.now(timezone.utc)


def _destino_seguro(destino):
    """Solo rutas relativas internas (evita redirecciones abiertas)."""
    if destino and destino.startswith("/") and not destino.startswith("//") and "\\" not in destino:
        return destino
    return url_for("main.inicio")


# ------------------------------------------------------------------ páginas
@bp.get("/login")
def login_page():
    if g.user:
        return redirect(url_for("main.inicio"))
    return render_template("login.html", next=request.args.get("next", ""))


@bp.get("/recuperar")
def recuperar_page():
    session.pop("rec_ok", None)
    return render_template("recuperar.html",
                           espera=current_app.config["CODIGO_REENVIO_SEG"])


@bp.get("/recuperar/validar")
def validar_page():
    if not session.get("rec_correo"):
        return redirect(url_for("auth.recuperar_page"))
    return render_template("validar.html", correo_mask=enmascarar_correo(session["rec_correo"]),
                           vigencia=current_app.config["CODIGO_VIGENCIA_MIN"],
                           espera=current_app.config["CODIGO_REENVIO_SEG"],
                           restante=_restante_reenvio())


@bp.get("/recuperar/nueva")
def nueva_page():
    if not session.get("rec_ok"):
        return redirect(url_for("auth.recuperar_page"))
    return render_template("nueva.html", requisitos=[(k, t) for k, t, _ in PASSWORD_REQUISITOS])


# ---------------------------------------------------------------------- login
@bp.post("/api/auth/login")
def api_login():
    datos = request.get_json(silent=True) or {}
    ident = limpiar_texto(datos.get("usuario")).lower()
    clave = datos.get("password")
    errores = {}
    if not ident:
        errores["usuario"] = "Ingresa tu usuario o correo."
    if not isinstance(clave, str) or not clave:
        errores["password"] = "Ingresa tu contraseña."
    if errores:
        return error_json(422, "validacion", "Completa los campos obligatorios.", errores)
    ident = ident[:120]
    ident_norm = normalizar(ident)
    espera = segundos_bloqueo_login(ident_norm)
    if espera:
        minutos = max(1, -(-espera // 60))
        return error_json(429, "bloqueado",
                          f"Demasiados intentos fallidos. Espera {minutos} minuto(s) antes de reintentar.",
                          reintentar_en=espera)
    db = get_db()
    fila = db.execute(
        "SELECT u.*, r.activo AS rol_activo, r.alcance FROM usuarios u JOIN roles r ON r.id=u.rol_id "
        "WHERE lower(u.usuario)=? OR lower(u.correo)=?", (ident, ident)).fetchone()
    valido = verificar_hash(fila["password_hash"] if fila else _HASH_RELLENO, clave)
    if not fila or not valido:
        registrar_intento_fallido(ident_norm)
        return error_json(401, "credenciales", MSJ_LOGIN_INVALIDO)
    if not fila["activo"] or not fila["rol_activo"]:
        return error_json(403, "cuenta_inactiva",
                          "Tu cuenta está inactiva. Contacta al administrador de tu delegación.")
    deleg = db.execute(
        "SELECT d.id FROM delegaciones d WHERE d.activo=1 AND (? = 'TODAS' OR d.id IN "
        "(SELECT delegacion_id FROM usuario_delegacion WHERE usuario_id=?)) ORDER BY d.codigo",
        (fila["alcance"], fila["id"])).fetchall()
    if not deleg:
        return error_json(403, "sin_delegacion",
                          "Tu cuenta no tiene una delegación activa asignada. Contacta al administrador.")
    limpiar_intentos(ident_norm)
    session.clear()
    token_csrf()
    session["uid"] = fila["id"]
    session["sv"] = fila["session_version"]
    ids = [d[0] for d in deleg]
    session["deleg"] = fila["ultima_delegacion_id"] if fila["ultima_delegacion_id"] in ids else ids[0]
    session.permanent = True
    return jsonify({"ok": True, "destino": _destino_seguro(datos.get("next"))})


@bp.post("/api/auth/logout")
def api_logout():
    session.clear()
    return jsonify({"ok": True, "destino": url_for("auth.login_page")})


# ------------------------------------------------------- recuperación: pasos
def _restante_reenvio():
    ultimo = session.get("rec_envio_ts", 0)
    return max(0, int(current_app.config["CODIGO_REENVIO_SEG"] - (time.time() - ultimo)))


def _emitir_codigo(correo):
    """Genera y envía un código si la cuenta existe y está activa. Nunca revela el resultado."""
    cfg = current_app.config
    db = get_db()
    fila = db.execute("SELECT id, nombre, activo FROM usuarios WHERE lower(correo)=?", (correo,)).fetchone()
    if not fila or not fila["activo"]:
        return
    ahora = _ahora()
    ultimo = db.execute("SELECT creado_en FROM recuperaciones WHERE usuario_id=? ORDER BY id DESC LIMIT 1",
                        (fila["id"],)).fetchone()
    if ultimo and (ahora - _dt(ultimo["creado_en"])).total_seconds() < cfg["CODIGO_REENVIO_SEG"]:
        return  # respeta la espera también si se borran las cookies
    ult_hora = db.execute("SELECT COUNT(*) FROM recuperaciones WHERE usuario_id=? AND creado_en>=?",
                          (fila["id"], _iso(ahora - timedelta(hours=1)))).fetchone()[0]
    if ult_hora >= cfg["CODIGO_MAX_SOLICITUDES_HORA"]:
        return
    codigo = f"{secrets.randbelow(10 ** 6):06d}"
    db.execute("UPDATE recuperaciones SET usado=1 WHERE usuario_id=? AND usado=0", (fila["id"],))
    db.execute("INSERT INTO recuperaciones (usuario_id, codigo_hash, expira_en, creado_en) VALUES (?,?,?,?)",
               (fila["id"], firmar_codigo(codigo), _iso(ahora + timedelta(minutes=cfg["CODIGO_VIGENCIA_MIN"])), _iso(ahora)))
    db.commit()
    enviar_correo(
        correo, "Código para recuperar tu contraseña · SGR",
        f"Hola {fila['nombre']},\n\nTu código de verificación es: {codigo}\n"
        f"Vence en {cfg['CODIGO_VIGENCIA_MIN']} minutos. Si no lo solicitaste, ignora este mensaje.\n\n"
        "Municipalidad de La Serena · Gestión de Atención Ciudadana")


@bp.post("/api/recuperar/solicitar")
def api_rec_solicitar():
    datos = request.get_json(silent=True) or {}
    correo = limpiar_texto(datos.get("correo")).lower()
    if not correo:
        return error_json(422, "validacion", "Ingresa el correo asociado a tu cuenta.", {"correo": "El correo es obligatorio."})
    if len(correo) > 120 or not EMAIL_RE.match(correo):
        return error_json(422, "validacion", "Ingresa un correo válido, por ejemplo nombre@dominio.cl.",
                          {"correo": "El formato del correo no es válido."})
    espera = _restante_reenvio() if session.get("rec_correo") == correo else 0
    if espera:
        return error_json(429, "espera", f"Podrás solicitar un nuevo código en {espera} segundos.", espera=espera)
    _emitir_codigo(correo)
    session["rec_correo"] = correo
    session["rec_envio_ts"] = time.time()
    session["rec_intentos"] = 0
    session.pop("rec_ok", None)
    return jsonify({"ok": True, "mensaje": MSJ_GENERICO_RECUPERAR, "destino": url_for("auth.validar_page")})


@bp.post("/api/recuperar/reenviar")
def api_rec_reenviar():
    correo = session.get("rec_correo")
    if not correo:
        return error_json(409, "sin_solicitud", "Inicia nuevamente el proceso de recuperación.")
    espera = _restante_reenvio()
    if espera:
        return error_json(429, "espera", f"Podrás reenviar el código en {espera} segundos.", espera=espera)
    _emitir_codigo(correo)
    session["rec_envio_ts"] = time.time()
    session["rec_intentos"] = 0
    return jsonify({"ok": True, "mensaje": "Si la cuenta existe, enviamos un nuevo código.",
                    "espera": current_app.config["CODIGO_REENVIO_SEG"]})


@bp.post("/api/recuperar/validar")
def api_rec_validar():
    cfg = current_app.config
    correo = session.get("rec_correo")
    if not correo:
        return error_json(409, "sin_solicitud", "Inicia nuevamente el proceso de recuperación.")
    datos = request.get_json(silent=True) or {}
    codigo = str(datos.get("codigo") or "").strip()
    if not (codigo.isdigit() and len(codigo) == 6):
        return error_json(422, "validacion", "Ingresa los 6 dígitos del código.", {"codigo": "El código tiene 6 dígitos."})
    # límite por sesión: también frena la prueba contra correos inexistentes
    if session.get("rec_intentos", 0) >= cfg["CODIGO_MAX_INTENTOS"]:
        return error_json(429, "intentos_agotados",
                          "Superaste los intentos permitidos. Solicita un nuevo código.", restantes=0)
    session["rec_intentos"] = session.get("rec_intentos", 0) + 1
    restantes = max(0, cfg["CODIGO_MAX_INTENTOS"] - session["rec_intentos"])
    db = get_db()
    fila = db.execute(
        "SELECT r.* FROM recuperaciones r JOIN usuarios u ON u.id=r.usuario_id "
        "WHERE lower(u.correo)=? AND r.usado=0 ORDER BY r.id DESC LIMIT 1", (correo,)).fetchone()
    mensaje_malo = "El código es incorrecto o venció. Revisa tu correo o solicita uno nuevo."
    if fila is None:
        return error_json(400, "codigo_invalido", mensaje_malo, restantes=restantes)
    if _ahora() > _dt(fila["expira_en"]):
        db.execute("UPDATE recuperaciones SET usado=1 WHERE id=?", (fila["id"],))
        db.commit()
        return error_json(400, "codigo_invalido", mensaje_malo, restantes=restantes)
    if fila["intentos"] >= cfg["CODIGO_MAX_INTENTOS"]:
        db.execute("UPDATE recuperaciones SET usado=1 WHERE id=?", (fila["id"],))
        db.commit()
        return error_json(429, "intentos_agotados", "Superaste los intentos permitidos. Solicita un nuevo código.", restantes=0)
    if firmar_codigo(codigo) != fila["codigo_hash"]:
        usado = 1 if fila["intentos"] + 1 >= cfg["CODIGO_MAX_INTENTOS"] else 0
        db.execute("UPDATE recuperaciones SET intentos=intentos+1, usado=? WHERE id=?", (usado, fila["id"]))
        db.commit()
        return error_json(400, "codigo_invalido", mensaje_malo, restantes=restantes)
    # código válido: se consume y se abre la etapa 3 con un token de un solo uso
    token = secrets.token_urlsafe(32)
    db.execute("UPDATE recuperaciones SET usado=1, verificado=1, token_hash=?, token_expira=? WHERE id=?",
               (firmar_codigo(token), _iso(_ahora() + timedelta(minutes=cfg["CODIGO_VIGENCIA_MIN"])), fila["id"]))
    db.commit()
    session["rec_ok"] = token
    session["rec_rid"] = fila["id"]
    return jsonify({"ok": True, "destino": url_for("auth.nueva_page")})


@bp.post("/api/recuperar/nueva")
def api_rec_nueva():
    token, rid = session.get("rec_ok"), session.get("rec_rid")
    if not token or not rid:
        return error_json(403, "no_verificado", "Primero verifica el código enviado a tu correo.")
    db = get_db()
    fila = db.execute("SELECT r.*, u.usuario, u.correo FROM recuperaciones r JOIN usuarios u ON u.id=r.usuario_id "
                      "WHERE r.id=?", (rid,)).fetchone()
    if (fila is None or not fila["verificado"] or not fila["token_hash"]
            or fila["token_hash"] != firmar_codigo(token) or _ahora() > _dt(fila["token_expira"])):
        session.pop("rec_ok", None)
        return error_json(403, "no_verificado", "La verificación venció. Solicita un nuevo código.")
    datos = request.get_json(silent=True) or {}
    clave, conf = datos.get("password"), datos.get("confirmacion")
    err = validar_password(clave, contexto=(fila["usuario"], fila["correo"].split("@")[0]))
    if err:
        return error_json(422, "validacion", err, {"password": err})
    if clave != conf:
        return error_json(422, "validacion", "La confirmación no coincide con la nueva contraseña.",
                          {"confirmacion": "Las contraseñas no coinciden."})
    db.execute("UPDATE usuarios SET password_hash=?, session_version=session_version+1 WHERE id=?",
               (hashear(clave), fila["usuario_id"]))
    # invalida el token y cualquier otro código pendiente del usuario
    db.execute("UPDATE recuperaciones SET usado=1, token_hash=NULL WHERE usuario_id=?", (fila["usuario_id"],))
    db.execute("DELETE FROM intentos_login WHERE identificador IN (?, ?)",
               (normalizar(fila["usuario"]), normalizar(fila["correo"])))
    db.commit()
    for k in ("rec_ok", "rec_rid", "rec_correo", "rec_envio_ts", "rec_intentos"):
        session.pop(k, None)
    return jsonify({"ok": True, "mensaje": "Tu contraseña se actualizó. Ya puedes iniciar sesión.",
                    "destino": url_for("auth.login_page")})
