"""Páginas autenticadas y API auxiliar (contexto, opciones de formularios, atención)."""
import json

from flask import (Blueprint, current_app, g, jsonify, render_template, request, session)

from .db import get_db
from .engine import ErrorNegocio
from .permisos import ACCIONES, MODULOS, MODULO_POR_CLAVE
from .resources import (ALCANCE_TEXTO, ALCANCES, RECURSOS, crear_atencion, buscar_vecinos, crear_vecino)
from .security import error_json, es_alcance_total, requiere, tiene
from .ui_config import ATENCIONES_LISTA, ESTADO_OPC, PANTALLAS, PENDIENTES

bp = Blueprint("main", __name__)


def _config_pantalla(clave):
    cfg = dict(PANTALLAS[clave])
    cfg["clave"] = clave
    cfg["slug"] = next(r.slug for r in RECURSOS if r.clave == clave)
    cfg["estados"] = ESTADO_OPC[cfg["genero"]]
    cfg["puede"] = {a: tiene(f"{clave}:{a}") for a, _ in ACCIONES}
    cfg["delegacion_activa"] = g.delegacion["id"]
    return cfg


# --------------------------------------------------------------------- páginas
@bp.get("/")
def inicio():
    db = get_db()
    resumen = {}
    if tiene("atenciones:ver"):
        resumen["atenciones_total"] = db.execute(
            "SELECT COUNT(*) FROM atenciones WHERE delegacion_id=?", (g.delegacion["id"],)).fetchone()[0]
        resumen["atenciones_hoy"] = db.execute(
            "SELECT COUNT(*) FROM atenciones WHERE delegacion_id=? AND date(fecha_registro, '-3 hours')=date('now','-3 hours')",
            (g.delegacion["id"],)).fetchone()[0]
    modulos_ok = [m for m in MODULOS if m[0] != "inicio" and tiene(f"{m[0]}:ver")]
    permisos_por_modulo = []
    for m in MODULOS:
        if m[0] == "inicio":
            continue
        acc = [etq for a, etq in ACCIONES if tiene(f"{m[0]}:{a}")]
        permisos_por_modulo.append({"modulo": m[1], "acciones": acc, "operativo": m[4]})
    return render_template("inicio.html", resumen=resumen, modulos_ok=modulos_ok,
                           permisos_por_modulo=permisos_por_modulo,
                           alcance_texto=ALCANCE_TEXTO[g.user["alcance"]])


def _pagina_crud(clave):
    return render_template("crud.html", cfg=_config_pantalla(clave), menu_activo=clave)


def _registrar_paginas_crud(app):
    for clave, cfg in PANTALLAS.items():
        modulo = MODULO_POR_CLAVE[clave]

        def vista(clave=clave):
            return _pagina_crud(clave)
        app.add_url_rule(modulo[3], f"pagina_{clave}", requiere(f"{clave}:ver")(vista), methods=["GET"])


def _registrar_paginas_pendientes(app):
    for clave, cfg in PENDIENTES.items():
        def vista(clave=clave):
            return render_template("pendiente.html", cfg=PENDIENTES[clave], menu_activo=clave)
        app.add_url_rule(cfg["ruta"], f"pagina_{clave}", requiere(f"{clave}:ver")(vista), methods=["GET"])


@bp.get("/atenciones")
@requiere("atenciones:ver")
def pagina_atenciones():
    cfg = dict(ATENCIONES_LISTA)
    cfg["clave"], cfg["slug"] = "atenciones", "atenciones"
    cfg["puede"] = {a: tiene(f"atenciones:{a}") for a, _ in ACCIONES}
    cfg["estados"] = []
    cfg["delegacion_activa"] = g.delegacion["id"]
    return render_template("atenciones.html", cfg=cfg, menu_activo="atenciones")


# ------------------------------------------------------------------ contexto
@bp.post("/api/contexto")
def api_cambiar_contexto():
    datos = request.get_json(silent=True) or {}
    try:
        nuevo = int(datos.get("delegacion_id"))
    except (TypeError, ValueError):
        return error_json(422, "validacion", "Selecciona una delegación.")
    destino = next((d for d in g.delegaciones if d["id"] == nuevo), None)
    if destino is None:  # validación en servidor: nada de saltar a delegaciones ajenas
        return error_json(403, "fuera_de_alcance", "No tienes autorización para operar en esa delegación.")
    session["deleg"] = nuevo
    db = get_db()
    db.execute("UPDATE usuarios SET ultima_delegacion_id=? WHERE id=?", (nuevo, g.user["id"]))
    db.commit()
    return jsonify({"ok": True, "delegacion": destino})


# ------------------------------------------------------- opciones de formularios
def _requiere_alguno(*perms):
    if not any(tiene(p) for p in perms):
        raise ErrorNegocio(403, "sin_permiso", "Tu perfil no tiene permiso para esta acción.")


@bp.get("/api/opciones/delegaciones")
def opciones_delegaciones():
    _requiere_alguno("usuarios:crear", "usuarios:editar")
    db = get_db()
    if es_alcance_total():
        filas = db.execute("SELECT id, codigo, nombre FROM delegaciones WHERE activo=1 ORDER BY codigo").fetchall()
        items = [dict(f) for f in filas]
    else:
        items = g.delegaciones
    return jsonify({"ok": True, "items": [{"id": d["id"], "texto": f"{d['codigo']} · {d['nombre']}"} for d in items]})


@bp.get("/api/opciones/roles")
def opciones_roles():
    _requiere_alguno("usuarios:crear", "usuarios:editar")
    filas = get_db().execute("SELECT id, codigo, nombre, alcance, permisos, activo FROM roles ORDER BY codigo").fetchall()
    mios = set(g.permisos)
    items = []
    for r in filas:
        asignable = (r["activo"] and ALCANCES[r["alcance"]] <= ALCANCES[g.user["alcance"]]
                     and set(json.loads(r["permisos"])) <= mios)
        if asignable:
            items.append({"id": r["id"], "texto": f"{r['nombre']} ({ALCANCE_TEXTO[r['alcance']].lower()})",
                          "alcance": r["alcance"]})
    return jsonify({"ok": True, "items": items})


@bp.get("/api/opciones/tipos")
def opciones_tipos():
    _requiere_alguno("subtipos:crear", "subtipos:editar")
    filas = get_db().execute("SELECT id, codigo, nombre FROM tipos_atencion WHERE activo=1 ORDER BY nombre").fetchall()
    return jsonify({"ok": True, "items": [{"id": f["id"], "texto": f"{f['codigo']} · {f['nombre']}"} for f in filas]})


@bp.get("/api/permisos/catalogo")
def catalogo_permisos():
    _requiere_alguno("roles:crear", "roles:editar", "roles:ver")
    return jsonify({
        "ok": True,
        "acciones": [{"k": k, "t": t} for k, t in ACCIONES],
        "modulos": [{"k": m[0], "t": m[1], "acciones": m[2], "operativo": m[4]} for m in MODULOS if m[0] != "inicio"],
        "propios": sorted(g.permisos),
        "alcance_max": g.user["alcance"],
    })


# ------------------------------------------------------------ ingreso de atención
@bp.get("/api/atencion/opciones")
@requiere("atenciones:crear")
def atencion_opciones():
    db = get_db()
    tipos = db.execute("SELECT id, codigo, nombre FROM tipos_atencion WHERE activo=1 ORDER BY nombre").fetchall()
    subs = db.execute("SELECT id, codigo, nombre, tipo_id FROM subatenciones WHERE activo=1 ORDER BY nombre").fetchall()
    return jsonify({
        "ok": True,
        "tipos": [dict(t) for t in tipos],
        "subtipos": [dict(s) for s in subs],
        "delegacion": g.delegacion,
        "responsable": g.user["nombre"],
    })


@bp.post("/api/atenciones")
@requiere("atenciones:crear")
def api_crear_atencion():
    res = crear_atencion(request.get_json(silent=True))
    cuerpo = {"ok": True, "atencion": res,
              "mensaje": f"La atención quedó registrada con el folio {res['folio']}."}
    resp = jsonify(cuerpo)
    resp.status_code = 200 if res.get("repetido") else 201
    return resp


@bp.get("/api/vecinos/buscar")
@requiere("atenciones:crear")
def api_buscar_vecinos():
    return jsonify({"ok": True, "items": buscar_vecinos(request.args.get("q", ""))})


@bp.post("/api/vecinos")
@requiere("atenciones:crear")
def api_crear_vecino():
    v = crear_vecino(request.get_json(silent=True))
    resp = jsonify({"ok": True, "item": v, "mensaje": "El solicitante quedó registrado."})
    resp.status_code = 201
    return resp


# ----------------------------------------------------------------- utilitarios
@bp.get("/salud")
def salud():
    """Chequeo para el balanceador/Target Group de AWS y para identificar la versión desplegada."""
    try:
        get_db().execute("SELECT 1").fetchone()
        bd = "ok"
    except Exception:  # pragma: no cover
        bd = "error"
    resp = jsonify({"estado": "ok" if bd == "ok" else "degradado", "base_de_datos": bd,
                    "version": current_app.config["APP_VERSION"], "commit": current_app.config["GIT_COMMIT"]})
    resp.status_code = 200 if bd == "ok" else 503
    return resp


@bp.get("/dev/bandeja")
def dev_bandeja():
    cfg = current_app.config
    if not cfg["DEV_OUTBOX"] or cfg["MAIL_MODE"] != "console":
        return render_template("error.html", codigo=404, titulo="No encontrado",
                               detalle="La página que buscas no existe."), 404
    filas = get_db().execute("SELECT * FROM bandeja_dev ORDER BY id DESC LIMIT 20").fetchall()
    return render_template("dev_bandeja.html", correos=filas)
