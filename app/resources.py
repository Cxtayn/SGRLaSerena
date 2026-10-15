"""Reglas de negocio de cada mantenedor y del ingreso de atención."""
import json
import re

from flask import g, session

from .db import ahora_iso, get_db
from .engine import ErrorNegocio, Recurso, fecha_local
from .permisos import validar_permisos
from .security import (es_alcance_total, hashear, ids_delegaciones_autorizadas)
from .validators import (EMAIL_RE, TELEFONO_RE, USUARIO_RE, limpiar_texto, normalizar_rut,
                         rut_valido, validar_password)

COMUNAS_COQUIMBO = [
    "La Serena", "Coquimbo", "Andacollo", "La Higuera", "Paiguano", "Vicuña", "Illapel", "Canela",
    "Los Vilos", "Salamanca", "Ovalle", "Combarbalá", "Monte Patria", "Punitaqui", "Río Hurtado",
]
ALCANCES = {"TODAS": 3, "ASIGNADAS": 2, "UNA": 1}
ALCANCE_TEXTO = {"TODAS": "Todas las delegaciones", "ASIGNADAS": "Delegaciones asignadas", "UNA": "Una delegación"}
SEP_F, SEP_R = "\x1f", "\x1e"


def _ids_asignados_actor():
    """Delegaciones asignadas al actor (None = todas, por alcance total)."""
    if es_alcance_total():
        return None
    filas = get_db().execute("SELECT delegacion_id FROM usuario_delegacion WHERE usuario_id=?",
                             (g.user["id"],)).fetchall()
    return [f[0] for f in filas] or [-1]


def _in(ids):
    return ",".join("?" * len(ids))


# ============================================================== Delegaciones
class Delegaciones(Recurso):
    clave, slug, tabla = "delegaciones", "delegaciones", "delegaciones"
    etiqueta, hoja = "Delegaciones", "Delegaciones"
    etiquetas_estado = ("Activa", "Inactiva")
    campos = [
        {"nombre": "codigo", "label": "Código", "tipo": "codigo"},
        {"nombre": "nombre", "label": "Nombre", "min": 3, "max": 100},
        {"nombre": "direccion", "label": "Dirección", "min": 5, "max": 150},
        {"nombre": "comuna", "label": "Comuna", "tipo": "choice", "opciones": COMUNAS_COQUIMBO},
    ]
    busqueda = ["t.codigo", "t.nombre", "t.direccion", "t.comuna",
                "CASE WHEN t.activo=1 THEN 'activa' ELSE 'inactiva' END"]
    ordenables = {"codigo": "t.codigo", "nombre": "t.nombre", "comuna": "t.comuna", "estado": "t.activo"}
    unicos = [("codigo", "Ya existe una delegación con ese código.")]
    export_cols = [("Código", "codigo"), ("Nombre", "nombre"), ("Dirección", "direccion"),
                   ("Comuna", "comuna"), ("Estado", "estado")]

    def condiciones(self, args):
        ids = _ids_asignados_actor()
        if ids is None:
            return [], []
        return [f"t.id IN ({_in(ids)})"], list(ids)

    def antes_de_actualizar(self, actual, limpio, datos):
        if limpio["activo"] == 0 and actual["id"] == g.delegacion["id"]:
            raise ErrorNegocio(409, "regla_negocio",
                               "No puedes desactivar la delegación activa de tu sesión. Cambia de contexto primero.")

    def antes_de_estado(self, actual, activo):
        if not activo and actual["id"] == g.delegacion["id"]:
            raise ErrorNegocio(409, "regla_negocio",
                               "No puedes desactivar la delegación activa de tu sesión. Cambia de contexto primero.")

    def antes_de_eliminar(self, actual):
        db = get_db()
        if actual["id"] == g.delegacion["id"]:
            raise ErrorNegocio(409, "regla_negocio", "No puedes eliminar la delegación activa de tu sesión.")
        n_u = db.execute("SELECT COUNT(*) FROM usuario_delegacion WHERE delegacion_id=?", (actual["id"],)).fetchone()[0]
        n_a = db.execute("SELECT COUNT(*) FROM atenciones WHERE delegacion_id=?", (actual["id"],)).fetchone()[0]
        if n_u or n_a:
            raise ErrorNegocio(409, "con_relaciones",
                               f"No se puede eliminar: tiene {n_u} usuario(s) y {n_a} atención(es) relacionadas. "
                               "Puedes desactivarla para conservar el historial.")


# ==================================================================== Roles
class Roles(Recurso):
    clave, slug, tabla = "roles", "roles", "roles"
    etiqueta, hoja = "Roles", "Roles"
    campos = [
        {"nombre": "codigo", "label": "Código", "tipo": "codigo"},
        {"nombre": "nombre", "label": "Nombre", "min": 3, "max": 60},
        {"nombre": "descripcion", "label": "Descripción", "max": 255, "requerido": False},
        {"nombre": "alcance", "label": "Alcance", "tipo": "choice", "opciones": list(ALCANCES)},
    ]
    busqueda = ["t.codigo", "t.nombre", "t.descripcion",
                "CASE t.alcance WHEN 'TODAS' THEN 'todas las delegaciones' "
                "WHEN 'ASIGNADAS' THEN 'delegaciones asignadas' ELSE 'una delegacion' END"]
    ordenables = {"codigo": "t.codigo", "nombre": "t.nombre", "alcance": "t.alcance", "estado": "t.activo"}
    unicos = [("codigo", "Ya existe un rol con ese código."), ("nombre", "Ya existe un rol con ese nombre.")]
    export_cols = [("Código", "codigo"), ("Rol", "nombre"), ("Descripción", "descripcion"),
                   ("Alcance", "alcance_texto"), ("Permisos", "permisos"), ("Usuarios", "n_usuarios"), ("Estado", "estado")]

    def seleccion(self):
        return "t.*, (SELECT COUNT(*) FROM usuarios u WHERE u.rol_id=t.id) AS n_usuarios"

    def serializar(self, f):
        d = super().serializar(f)
        d["permisos"] = json.loads(f["permisos"] or "[]")
        d["alcance_texto"] = ALCANCE_TEXTO.get(f["alcance"], f["alcance"])
        d["n_usuarios"] = f["n_usuarios"]
        return d

    # --- control de escalamiento de privilegios
    def _gobierna(self, rol_fila_o_dict):
        permisos = set(json.loads(rol_fila_o_dict["permisos"] or "[]")) if "permisos" in rol_fila_o_dict.keys() else set()
        return (ALCANCES[rol_fila_o_dict["alcance"]] <= ALCANCES[g.user["alcance"]]
                and permisos <= set(g.permisos))

    def validar_extra(self, datos, limpio, errores, actual):
        if "permisos" in datos or actual is None:
            perm, err = validar_permisos(datos.get("permisos", []))
            if err:
                errores["permisos"] = err
            else:
                if not perm:
                    errores["permisos"] = "Selecciona al menos un permiso."
                excedente = set(perm) - set(g.permisos)
                if excedente:
                    errores["permisos"] = "No puedes otorgar permisos que tu propio perfil no tiene."
                limpio["permisos"] = json.dumps(perm)
        else:
            limpio["permisos"] = actual["permisos"]
        a = limpio.get("alcance")
        if a in ALCANCES and ALCANCES[a] > ALCANCES[g.user["alcance"]]:
            errores["alcance"] = "No puedes definir un alcance mayor al de tu propio perfil."

    def _proteger(self, actual):
        if actual["id"] == g.user["rol_id"]:
            raise ErrorNegocio(403, "regla_negocio", "No puedes modificar ni eliminar tu propio rol.")
        if not self._gobierna(actual):
            raise ErrorNegocio(403, "regla_negocio", "Este rol tiene más privilegios que tu perfil; no puedes administrarlo.")

    def antes_de_actualizar(self, actual, limpio, datos):
        self._proteger(actual)
        if limpio["activo"] == 0 and actual["n_usuarios"]:
            n = get_db().execute("SELECT COUNT(*) FROM usuarios WHERE rol_id=? AND activo=1", (actual["id"],)).fetchone()[0]
            if n:
                raise ErrorNegocio(409, "regla_negocio", f"No se puede desactivar: {n} usuario(s) activo(s) usan este rol.")

    def antes_de_estado(self, actual, activo):
        self._proteger(actual)
        if not activo:
            n = get_db().execute("SELECT COUNT(*) FROM usuarios WHERE rol_id=? AND activo=1", (actual["id"],)).fetchone()[0]
            if n:
                raise ErrorNegocio(409, "regla_negocio", f"No se puede desactivar: {n} usuario(s) activo(s) usan este rol.")

    def antes_de_eliminar(self, actual):
        self._proteger(actual)
        if actual["n_usuarios"]:
            raise ErrorNegocio(409, "con_relaciones",
                               f"No se puede eliminar: {actual['n_usuarios']} usuario(s) tienen este rol. Puedes desactivarlo.")


# ================================================================== Usuarios
class Usuarios(Recurso):
    clave, slug, tabla = "usuarios", "usuarios", "usuarios"
    etiqueta, hoja = "Usuarios", "Usuarios"
    campos = [{"nombre": "nombre", "label": "Nombre", "min": 3, "max": 100}]
    busqueda = ["t.usuario", "t.nombre", "t.correo", "r.nombre",
                "(SELECT GROUP_CONCAT(d.codigo || ' ' || d.nombre, ' ') FROM usuario_delegacion ud "
                "JOIN delegaciones d ON d.id=ud.delegacion_id WHERE ud.usuario_id=t.id)",
                "CASE WHEN t.activo=1 THEN 'activo' ELSE 'inactivo' END"]
    ordenables = {"nombre": "t.nombre", "correo": "t.correo", "usuario": "t.usuario", "rol": "r.nombre", "estado": "t.activo"}
    orden_defecto = "t.nombre"
    unicos = [("usuario", "Ya existe un usuario con ese nombre de usuario."),
              ("correo", "Ya existe un usuario con ese correo.")]
    # Nunca se exporta: password_hash, session_version ni campos internos.
    export_cols = [("Usuario", "usuario"), ("Nombre", "nombre"), ("Correo", "correo"), ("Rol", "rol"),
                   ("Delegaciones", "delegaciones_texto"), ("Estado", "estado")]

    def desde(self):
        return "FROM usuarios t JOIN roles r ON r.id=t.rol_id"

    def seleccion(self):
        return ("t.id, t.usuario, t.nombre, t.correo, t.rol_id, t.activo, r.nombre AS rol_nombre, "
                "r.alcance AS rol_alcance, "
                f"(SELECT GROUP_CONCAT(d.id || char(31) || d.codigo || char(31) || d.nombre, char(30)) "
                "FROM usuario_delegacion ud JOIN delegaciones d ON d.id=ud.delegacion_id "
                "WHERE ud.usuario_id=t.id) AS deleg_raw")

    def condiciones(self, args):
        ids = _ids_asignados_actor()
        amplio = args.get("_detalle") or args.get("ambito") == "autorizadas"
        if amplio:
            if ids is None:
                return [], []
            return [f"t.id IN (SELECT usuario_id FROM usuario_delegacion WHERE delegacion_id IN ({_in(ids)}))"], list(ids)
        return ["t.id IN (SELECT usuario_id FROM usuario_delegacion WHERE delegacion_id = ?)"], [g.delegacion["id"]]

    def serializar(self, f):
        deleg = []
        for raw in (f["deleg_raw"] or "").split(SEP_R):
            if raw:
                i, c, n = raw.split(SEP_F)
                deleg.append({"id": int(i), "codigo": c, "nombre": n})
        deleg.sort(key=lambda x: x["codigo"])
        return {
            "id": f["id"], "usuario": f["usuario"], "nombre": f["nombre"], "correo": f["correo"],
            "rol_id": f["rol_id"], "rol": f["rol_nombre"], "rol_alcance": f["rol_alcance"],
            "delegaciones": deleg, "delegaciones_ids": [d["id"] for d in deleg],
            "delegaciones_texto": ", ".join(f"{d['codigo']} · {d['nombre']}" for d in deleg),
            "activo": bool(f["activo"]), "estado": "Activo" if f["activo"] else "Inactivo",
        }

    def valor_export(self, d, clave):
        return d.get(clave, "")

    # ---------------------------------------------------------- validación
    def _rol_asignable(self, rol):
        """Evita escalamiento: el rol no puede superar alcance ni permisos del actor."""
        permisos = set(json.loads(rol["permisos"] or "[]"))
        return ALCANCES[rol["alcance"]] <= ALCANCES[g.user["alcance"]] and permisos <= set(g.permisos)

    def validar_extra(self, datos, limpio, errores, actual):
        db = get_db()
        usuario = limpiar_texto(datos.get("usuario", actual["usuario"] if actual else "")).lower()
        if not USUARIO_RE.match(usuario):
            errores["usuario"] = "Usa de 3 a 30 caracteres: minúsculas, números, punto, guion o guion bajo."
        limpio["usuario"] = usuario
        correo = limpiar_texto(datos.get("correo", actual["correo"] if actual else "")).lower()
        if not correo:
            errores["correo"] = "El correo es obligatorio."
        elif len(correo) > 120 or not EMAIL_RE.match(correo):
            errores["correo"] = "Ingresa un correo válido, por ejemplo nombre@dominio.cl."
        limpio["correo"] = correo

        rol = None
        try:
            rol_id = int(datos.get("rol_id", actual["rol_id"] if actual else 0))
        except (TypeError, ValueError):
            rol_id = 0
        rol = db.execute("SELECT * FROM roles WHERE id=?", (rol_id,)).fetchone()
        if rol is None:
            errores["rol_id"] = "Selecciona un rol."
        elif actual is None or rol_id != actual["rol_id"]:
            if not rol["activo"]:
                errores["rol_id"] = "El rol seleccionado está inactivo."
            elif not self._rol_asignable(rol):
                errores["rol_id"] = "No puedes asignar un rol con más privilegios que tu propio perfil."
        limpio["rol_id"] = rol_id

        # delegaciones
        entrada = datos.get("delegaciones_ids", None)
        if entrada is None and actual is not None:
            entrada = [r[0] for r in db.execute("SELECT delegacion_id FROM usuario_delegacion WHERE usuario_id=?", (actual["id"],))]
        if not isinstance(entrada, list):
            entrada = []
        try:
            pedidas = sorted({int(x) for x in entrada})
        except (TypeError, ValueError):
            pedidas = []
            errores["delegaciones_ids"] = "Las delegaciones enviadas no son válidas."
        asignables = {d["id"] for d in g.delegaciones}
        if not es_alcance_total():
            ajenas = [i for i in pedidas if i not in asignables]
            if ajenas:
                errores["delegaciones_ids"] = "Solo puedes asignar delegaciones a las que tienes acceso."
        else:
            existentes = {r[0] for r in db.execute("SELECT id FROM delegaciones WHERE activo=1")}
            if any(i not in existentes for i in pedidas):
                errores["delegaciones_ids"] = "Hay delegaciones inexistentes o inactivas."
        final = set(pedidas)
        if actual is not None and not es_alcance_total():
            # conserva las delegaciones del usuario que quedan fuera del alcance del actor
            previas = {r[0] for r in db.execute("SELECT delegacion_id FROM usuario_delegacion WHERE usuario_id=?", (actual["id"],))}
            asign_todas = set(_ids_asignados_actor() or [])
            final |= {i for i in previas if i not in asign_todas}
        if "delegaciones_ids" not in errores:
            if not final:
                errores["delegaciones_ids"] = "Asigna al menos una delegación."
            elif rol is not None and rol["alcance"] == "UNA" and len(final) != 1:
                errores["delegaciones_ids"] = "El rol seleccionado permite exactamente una delegación."
        limpio["_delegaciones"] = sorted(final)

        # contraseña
        clave = datos.get("password")
        if actual is None or clave:
            err = validar_password(clave, contexto=(usuario, correo.split("@")[0]))
            if err:
                errores["password"] = err
            else:
                limpio["password_hash"] = hashear(clave)
                limpio["_nueva_clave"] = True

        # autoprotección
        if actual is not None and actual["id"] == g.user["id"]:
            if limpio.get("rol_id") != actual["rol_id"] or limpio.get("activo") == 0:
                errores["rol_id"] = "No puedes cambiar tu propio rol ni desactivar tu propia cuenta."

    def antes_de_actualizar(self, actual, limpio, datos):
        pass

    def despues_de_guardar(self, rid, limpio, datos, actual):
        db = get_db()
        db.execute("DELETE FROM usuario_delegacion WHERE usuario_id=?", (rid,))
        for did in limpio["_delegaciones"]:
            db.execute("INSERT INTO usuario_delegacion (usuario_id, delegacion_id) VALUES (?,?)", (rid, did))
        ultima = db.execute("SELECT ultima_delegacion_id FROM usuarios WHERE id=?", (rid,)).fetchone()[0]
        if ultima not in limpio["_delegaciones"]:
            db.execute("UPDATE usuarios SET ultima_delegacion_id=? WHERE id=?", (limpio["_delegaciones"][0], rid))
        if limpio.get("_nueva_clave") and actual is not None:
            db.execute("UPDATE usuarios SET session_version = session_version + 1 WHERE id=?", (rid,))
            if rid == g.user["id"]:
                nueva = db.execute("SELECT session_version FROM usuarios WHERE id=?", (rid,)).fetchone()[0]
                session["sv"] = nueva

    def antes_de_estado(self, actual, activo):
        if actual["id"] == g.user["id"] and not activo:
            raise ErrorNegocio(409, "regla_negocio", "No puedes desactivar tu propia cuenta.")
        if not activo and actual["rol_alcance"] == "TODAS":
            quedan = get_db().execute(
                "SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id=u.rol_id "
                "WHERE r.alcance='TODAS' AND u.activo=1 AND u.id<>?", (actual["id"],)).fetchone()[0]
            if not quedan:
                raise ErrorNegocio(409, "regla_negocio", "Debe quedar al menos un usuario activo con alcance total.")

    def antes_de_eliminar(self, actual):
        if actual["id"] == g.user["id"]:
            raise ErrorNegocio(409, "regla_negocio", "No puedes eliminar tu propia cuenta.")
        n = get_db().execute("SELECT COUNT(*) FROM atenciones WHERE usuario_id=?", (actual["id"],)).fetchone()[0]
        if n:
            raise ErrorNegocio(409, "con_relaciones",
                               f"No se puede eliminar: registró {n} atención(es). Desactívalo para conservar el historial.")
        if actual["rol_alcance"] == "TODAS":
            quedan = get_db().execute(
                "SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id=u.rol_id "
                "WHERE r.alcance='TODAS' AND u.activo=1 AND u.id<>?", (actual["id"],)).fetchone()[0]
            if not quedan:
                raise ErrorNegocio(409, "regla_negocio", "Debe quedar al menos un usuario activo con alcance total.")


# ============================================================ Ítems y metas
class Items(Recurso):
    clave, slug, tabla = "items", "items", "items"
    etiqueta, hoja = "Ítems y metas", "Items y metas"
    campos = [
        {"nombre": "codigo", "label": "Código", "tipo": "codigo"},
        {"nombre": "nombre", "label": "Nombre", "min": 3, "max": 100},
        {"nombre": "descripcion", "label": "Descripción", "max": 255, "requerido": False},
    ]
    busqueda = ["t.codigo", "t.nombre", "t.descripcion", "CASE WHEN t.activo=1 THEN 'activo' ELSE 'inactivo' END"]
    ordenables = {"codigo": "t.codigo", "nombre": "t.nombre", "estado": "t.activo"}
    unicos = [("codigo", "Ya existe un ítem con ese código.")]
    export_cols = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"), ("Estado", "estado")]


# ========================================================== Tipo de atención
class Tipos(Recurso):
    clave, slug, tabla = "tipos", "tipos-atencion", "tipos_atencion"
    etiqueta, hoja = "Tipo de Atención", "Tipos de atencion"
    campos = [
        {"nombre": "codigo", "label": "Código", "tipo": "codigo"},
        {"nombre": "nombre", "label": "Nombre", "min": 3, "max": 60},
        {"nombre": "descripcion", "label": "Descripción", "max": 255, "requerido": False},
    ]
    busqueda = ["t.codigo", "t.nombre", "t.descripcion", "CASE WHEN t.activo=1 THEN 'activo' ELSE 'inactivo' END"]
    ordenables = {"codigo": "t.codigo", "nombre": "t.nombre", "estado": "t.activo"}
    unicos = [("codigo", "Ya existe un tipo con ese código."), ("nombre", "Ya existe un tipo con ese nombre.")]
    export_cols = [("Código", "codigo"), ("Nombre", "nombre"), ("Descripción", "descripcion"),
                   ("Subatenciones", "n_subs"), ("Estado", "estado")]

    def seleccion(self):
        return "t.*, (SELECT COUNT(*) FROM subatenciones s WHERE s.tipo_id=t.id) AS n_subs"

    def serializar(self, f):
        d = super().serializar(f)
        d["n_subs"] = f["n_subs"]
        return d

    def _validar_desactivacion(self, actual, activo):
        if not activo:
            n = get_db().execute("SELECT COUNT(*) FROM subatenciones WHERE tipo_id=? AND activo=1", (actual["id"],)).fetchone()[0]
            if n:
                raise ErrorNegocio(409, "regla_negocio",
                                   f"No se puede desactivar: tiene {n} subatención(es) activa(s). Desactívalas primero.")

    def antes_de_actualizar(self, actual, limpio, datos):
        self._validar_desactivacion(actual, bool(limpio["activo"]))

    def antes_de_estado(self, actual, activo):
        self._validar_desactivacion(actual, activo)

    def antes_de_eliminar(self, actual):
        if actual["n_subs"]:
            raise ErrorNegocio(409, "con_relaciones",
                               f"No se puede eliminar: tiene {actual['n_subs']} subatención(es) asociada(s).")
        if get_db().execute("SELECT 1 FROM atenciones WHERE tipo_id=? LIMIT 1", (actual["id"],)).fetchone():
            raise ErrorNegocio(409, "con_relaciones", "No se puede eliminar: tiene atenciones registradas. Puedes desactivarlo.")


# ================================================================ Sub atención
class Subtipos(Recurso):
    clave, slug, tabla = "subtipos", "sub-atenciones", "subatenciones"
    etiqueta, hoja = "Sub Atención", "Sub atenciones"
    etiquetas_estado = ("Activa", "Inactiva")
    campos = [
        {"nombre": "codigo", "label": "Código", "tipo": "codigo"},
        {"nombre": "nombre", "label": "Nombre", "min": 3, "max": 80},
    ]
    busqueda = ["t.codigo", "t.nombre", "ta.nombre", "ta.codigo",
                "CASE WHEN t.activo=1 THEN 'activa' ELSE 'inactiva' END"]
    ordenables = {"codigo": "t.codigo", "nombre": "t.nombre", "tipo": "ta.nombre", "estado": "t.activo"}
    unicos = [("codigo", "Ya existe una subatención con ese código.")]
    export_cols = [("Código", "codigo"), ("Nombre", "nombre"), ("Tipo de Atención", "tipo_nombre"), ("Estado", "estado")]

    def desde(self):
        return "FROM subatenciones t JOIN tipos_atencion ta ON ta.id=t.tipo_id"

    def seleccion(self):
        return ("t.*, ta.nombre AS tipo_nombre, ta.codigo AS tipo_codigo, ta.activo AS tipo_activo, "
                "(SELECT COUNT(*) FROM atenciones a WHERE a.subtipo_id=t.id) AS n_atenciones")

    def serializar(self, f):
        d = super().serializar(f)
        d.update(tipo_id=f["tipo_id"], tipo_nombre=f["tipo_nombre"], tipo_codigo=f["tipo_codigo"],
                 n_atenciones=f["n_atenciones"])
        return d

    def validar_extra(self, datos, limpio, errores, actual):
        db = get_db()
        try:
            tid = int(datos.get("tipo_id", actual["tipo_id"] if actual else 0))
        except (TypeError, ValueError):
            tid = 0
        tipo = db.execute("SELECT * FROM tipos_atencion WHERE id=?", (tid,)).fetchone()
        if tipo is None:
            errores["tipo_id"] = "Selecciona un Tipo de Atención."
        else:
            if limpio.get("activo", 1) and not tipo["activo"]:
                errores["tipo_id"] = "El Tipo de Atención está inactivo; una subatención activa necesita un tipo activo."
            if actual is not None and tid != actual["tipo_id"] and actual["n_atenciones"]:
                errores["tipo_id"] = "No se puede cambiar el tipo: la subatención ya tiene atenciones registradas."
            if "nombre" in limpio and limpio["nombre"]:
                dup = db.execute("SELECT id FROM subatenciones WHERE tipo_id=? AND norm(nombre)=norm(?) AND id<>?",
                                 (tid, limpio["nombre"], actual["id"] if actual else -1)).fetchone()
                if dup:
                    errores["nombre"] = "Ya existe una subatención con ese nombre en el mismo Tipo de Atención."
        limpio["tipo_id"] = tid

    def antes_de_estado(self, actual, activo):
        if activo and not actual["tipo_activo"]:
            raise ErrorNegocio(409, "regla_negocio", "No se puede activar: su Tipo de Atención está inactivo.")

    def antes_de_eliminar(self, actual):
        if actual["n_atenciones"]:
            raise ErrorNegocio(409, "con_relaciones",
                               f"No se puede eliminar: tiene {actual['n_atenciones']} atención(es) registradas. Puedes desactivarla.")


# ================================================================ Atenciones
class Atenciones(Recurso):
    clave, slug, tabla = "atenciones", "atenciones", "atenciones"
    etiqueta, hoja = "Atenciones", "Atenciones"
    solo_lectura = True
    filtra_estado = False
    orden_defecto = "t.id DESC"
    busqueda = ["t.folio", "v.nombres", "v.apellidos", "v.rut", "ta.nombre", "sa.nombre", "t.descripcion", "u.nombre"]
    ordenables = {"folio": "t.id", "fecha": "t.fecha_registro", "solicitante": "v.apellidos",
                  "tipo": "ta.nombre", "subtipo": "sa.nombre"}
    export_cols = [("Folio", "folio"), ("Fecha y hora", "fecha"), ("Solicitante", "solicitante"), ("RUT", "rut"),
                   ("Tipo de Atención", "tipo"), ("Sub Atención", "subtipo"), ("Descripción", "descripcion"),
                   ("Delegación", "delegacion"), ("Responsable", "responsable")]

    def desde(self):
        return ("FROM atenciones t JOIN vecinos v ON v.id=t.vecino_id JOIN tipos_atencion ta ON ta.id=t.tipo_id "
                "JOIN subatenciones sa ON sa.id=t.subtipo_id JOIN usuarios u ON u.id=t.usuario_id "
                "JOIN delegaciones d ON d.id=t.delegacion_id")

    def seleccion(self):
        return ("t.id, t.folio, t.descripcion, t.fecha_registro, t.delegacion_id, v.nombres, v.apellidos, v.rut, "
                "ta.nombre AS tipo, sa.nombre AS subtipo, u.nombre AS responsable, d.codigo AS d_cod, d.nombre AS d_nom")

    def condiciones(self, args):
        if args.get("_detalle") or args.get("ambito") == "autorizadas":
            ids = ids_delegaciones_autorizadas()
            if es_alcance_total():
                return [], []
            return [f"t.delegacion_id IN ({_in(ids)})"], list(ids)
        return ["t.delegacion_id = ?"], [g.delegacion["id"]]

    def serializar(self, f):
        return {
            "id": f["id"], "folio": f["folio"], "fecha": fecha_local(f["fecha_registro"]),
            "fecha_iso": f["fecha_registro"], "solicitante": f"{f['nombres']} {f['apellidos']}", "rut": f["rut"],
            "tipo": f["tipo"], "subtipo": f["subtipo"], "descripcion": f["descripcion"],
            "delegacion": f"{f['d_cod']} · {f['d_nom']}", "delegacion_id": f["delegacion_id"],
            "responsable": f["responsable"],
        }

    def obtener(self, rid, *, exigir=True):
        fila = super().obtener(rid, exigir=exigir)
        return fila


def crear_atencion(datos):
    """Registra una atención. Delegación, responsable y fecha las fija el servidor."""
    if not isinstance(datos, dict):
        raise ErrorNegocio(400, "solicitud_invalida", "El cuerpo de la solicitud no es válido.")
    db = get_db()
    errores = {}
    if datos.get("delegacion_id") not in (None, "", g.delegacion["id"]):
        raise ErrorNegocio(403, "fuera_de_alcance", "La delegación enviada no coincide con tu contexto autorizado.")
    if datos.get("usuario_id") not in (None, "", g.user["id"]):
        raise ErrorNegocio(403, "fuera_de_alcance", "El responsable lo asigna el sistema: no puede modificarse.")

    def _entero(clave):
        try:
            return int(datos.get(clave))
        except (TypeError, ValueError):
            return 0

    vecino = db.execute("SELECT * FROM vecinos WHERE id=?", (_entero("vecino_id"),)).fetchone()
    if vecino is None:
        errores["vecino_id"] = "Selecciona o registra al solicitante."
    elif not vecino["activo"]:
        errores["vecino_id"] = "El solicitante está inactivo."
    tipo = db.execute("SELECT * FROM tipos_atencion WHERE id=?", (_entero("tipo_id"),)).fetchone()
    if tipo is None:
        errores["tipo_id"] = "Selecciona el Tipo de Atención."
    elif not tipo["activo"]:
        errores["tipo_id"] = "El Tipo de Atención seleccionado está inactivo."
    sub = db.execute("SELECT * FROM subatenciones WHERE id=?", (_entero("subtipo_id"),)).fetchone()
    if sub is None:
        errores["subtipo_id"] = "Selecciona la Sub Atención."
    elif not sub["activo"]:
        errores["subtipo_id"] = "La Sub Atención seleccionada está inactiva."
    elif tipo is not None and sub["tipo_id"] != tipo["id"]:
        errores["subtipo_id"] = "La Sub Atención no corresponde al Tipo de Atención elegido."
    descripcion = re.sub(r"[ \t]+", " ", str(datos.get("descripcion") or "")).strip()
    if not (10 <= len(descripcion) <= 2000):
        errores["descripcion"] = "La descripción debe tener entre 10 y 2000 caracteres."
    token = str(datos.get("token_envio") or "")[:64] or None
    if errores:
        raise ErrorNegocio(422, "validacion", "Revisa los campos marcados.", errores)

    if token:
        previa = db.execute("SELECT id, folio, fecha_registro FROM atenciones WHERE token_envio=? AND usuario_id=?",
                            (token, g.user["id"])).fetchone()
        if previa:  # doble envío: se devuelve el mismo resultado sin crear otro registro
            return {"id": previa["id"], "folio": previa["folio"], "fecha": fecha_local(previa["fecha_registro"]),
                    "repetido": True, "delegacion": f"{g.delegacion['codigo']} · {g.delegacion['nombre']}",
                    "responsable": g.user["nombre"]}
    ahora = ahora_iso()
    try:
        cur = db.execute(
            "INSERT INTO atenciones (vecino_id, tipo_id, subtipo_id, descripcion, delegacion_id, usuario_id, token_envio, fecha_registro) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (vecino["id"], tipo["id"], sub["id"], descripcion, g.delegacion["id"], g.user["id"], token, ahora))
        rid = cur.lastrowid
        folio = f"ATN-{ahora[:4]}-{rid:06d}"
        db.execute("UPDATE atenciones SET folio=? WHERE id=?", (folio, rid))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"id": rid, "folio": folio, "fecha": fecha_local(ahora), "repetido": False,
            "delegacion": f"{g.delegacion['codigo']} · {g.delegacion['nombre']}", "responsable": g.user["nombre"]}


# ================================================================== Vecinos
def _serializar_vecino(f):
    return {"id": f["id"], "rut": f["rut"], "nombres": f["nombres"], "apellidos": f["apellidos"],
            "nombre_completo": f"{f['nombres']} {f['apellidos']}", "correo": f["correo"] or "", "telefono": f["telefono"] or ""}


def buscar_vecinos(q):
    from .db import normalizar
    q = limpiar_texto(q)[:60]
    if len(q) < 2:
        return []
    cond, params = [], []
    for tok in normalizar(q).replace(".", "").split()[:5]:
        esc = tok.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        cond.append("(norm(nombres) LIKE ? ESCAPE '\\' OR norm(apellidos) LIKE ? ESCAPE '\\' "
                    "OR norm(REPLACE(rut,'.','')) LIKE ? ESCAPE '\\')")
        params += [f"%{esc}%"] * 3
    filas = get_db().execute(
        f"SELECT * FROM vecinos WHERE activo=1 AND {' AND '.join(cond)} ORDER BY apellidos, nombres LIMIT 10", params).fetchall()
    return [_serializar_vecino(f) for f in filas]


def crear_vecino(datos):
    if not isinstance(datos, dict):
        raise ErrorNegocio(400, "solicitud_invalida", "El cuerpo de la solicitud no es válido.")
    errores = {}
    rut = normalizar_rut(datos.get("rut"))
    if not rut_valido(rut):
        errores["rut"] = "Ingresa un RUT válido, por ejemplo 12345678-5."
    nombres = limpiar_texto(datos.get("nombres"))
    apellidos = limpiar_texto(datos.get("apellidos"))
    if not (2 <= len(nombres) <= 80):
        errores["nombres"] = "Los nombres deben tener entre 2 y 80 caracteres."
    if not (2 <= len(apellidos) <= 80):
        errores["apellidos"] = "Los apellidos deben tener entre 2 y 80 caracteres."
    correo = limpiar_texto(datos.get("correo")).lower()
    if correo and (len(correo) > 120 or not EMAIL_RE.match(correo)):
        errores["correo"] = "Ingresa un correo válido o deja el campo vacío."
    telefono = limpiar_texto(datos.get("telefono"))
    if telefono and not TELEFONO_RE.match(telefono):
        errores["telefono"] = "Ingresa un teléfono válido (8 a 15 dígitos)."
    if errores:
        raise ErrorNegocio(422, "validacion", "Revisa los campos marcados.", errores)
    db = get_db()
    existente = db.execute("SELECT * FROM vecinos WHERE rut=?", (rut,)).fetchone()
    if existente:
        raise ErrorNegocio(409, "duplicado", "Ya existe un solicitante con ese RUT. Búscalo por RUT o nombre.",
                           {"rut": "Este RUT ya está registrado."})
    cur = db.execute("INSERT INTO vecinos (rut, nombres, apellidos, correo, telefono) VALUES (?,?,?,?,?)",
                     (rut, nombres, apellidos, correo or None, telefono or None))
    db.commit()
    return _serializar_vecino(db.execute("SELECT * FROM vecinos WHERE id=?", (cur.lastrowid,)).fetchone())


RECURSOS = [Delegaciones(), Roles(), Usuarios(), Items(), Tipos(), Subtipos(), Atenciones()]
