"""Catálogo de módulos y acciones. Fuente única para menú, roles y validación."""

ACCIONES = [("ver", "Ver"), ("crear", "Crear"), ("editar", "Editar"),
            ("eliminar", "Eliminar"), ("exportar", "Exportar")]

# clave, etiqueta, acciones disponibles, ruta, operativo
MODULOS = [
    ("inicio", "Inicio", ["ver"], "/", True),
    ("delegaciones", "Delegaciones", ["ver", "crear", "editar", "eliminar", "exportar"], "/delegaciones", True),
    ("roles", "Roles", ["ver", "crear", "editar", "eliminar", "exportar"], "/roles", True),
    ("usuarios", "Usuarios", ["ver", "crear", "editar", "eliminar", "exportar"], "/usuarios", True),
    ("items", "Ítems y metas", ["ver", "crear", "editar", "eliminar", "exportar"], "/items", True),
    ("tipos", "Tipo de Atención", ["ver", "crear", "editar", "eliminar", "exportar"], "/tipos-atencion", True),
    ("subtipos", "Sub Atención", ["ver", "crear", "editar", "eliminar", "exportar"], "/sub-atenciones", True),
    ("atenciones", "Atenciones", ["ver", "crear", "exportar"], "/atenciones", True),
    # Plantillas de módulos pendientes (solo navegación y visualización diferenciada)
    ("vecinos", "Vecinos", ["ver"], "/vecinos", False),
    ("gestion_tipos", "Tipos de Gestión", ["ver"], "/tipos-gestion", False),
    ("seguimiento", "Seguimiento de casos", ["ver"], "/seguimiento", False),
    ("reportes", "Reportes", ["ver"], "/reportes", False),
]

MODULO_POR_CLAVE = {m[0]: m for m in MODULOS}
TODOS_LOS_PERMISOS = {f"{m[0]}:{a}" for m in MODULOS for a in m[2]}


def validar_permisos(lista):
    """Devuelve (permisos_normalizados, error|None)."""
    if not isinstance(lista, list):
        return None, "Los permisos deben enviarse como una lista."
    limpio = sorted(set(lista))
    for p in limpio:
        if p not in TODOS_LOS_PERMISOS:
            return None, f"Permiso desconocido: {p}."
    por_modulo = {}
    for p in limpio:
        mod, acc = p.split(":")
        por_modulo.setdefault(mod, set()).add(acc)
    for mod, accs in por_modulo.items():
        if accs - {"ver"} and "ver" not in accs:
            etiqueta = MODULO_POR_CLAVE[mod][1]
            return None, f"En «{etiqueta}» toda acción requiere también el permiso Ver."
    return limpio, None
