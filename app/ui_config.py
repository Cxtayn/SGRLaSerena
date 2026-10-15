"""Descripción declarativa de cada pantalla (columnas y formularios).
El JavaScript genérico (crud.js) construye tabla, filtros y formularios a partir de esto;
las reglas de validación reales viven en el servidor (resources.py)."""
from .resources import ALCANCE_TEXTO, COMUNAS_COQUIMBO

ESTADO_OPC = {"m": ["Activo", "Inactivo"], "f": ["Activa", "Inactiva"]}

PANTALLAS = {
    "delegaciones": {
        "titulo": "Delegaciones municipales", "migas": "Delegaciones", "singular": "delegación", "genero": "f",
        "columnas": [
            {"k": "codigo", "t": "Código", "sort": "codigo"},
            {"k": "nombre", "t": "Nombre", "sort": "nombre"},
            {"k": "comuna", "t": "Comuna", "sort": "comuna"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "codigo", "t": "Código", "tipo": "texto", "req": True, "max": 20, "mayus": True,
             "ayuda": "Ej.: DEL01. Letras mayúsculas, números, guion."},
            {"k": "nombre", "t": "Nombre", "tipo": "texto", "req": True, "max": 100},
            {"k": "direccion", "t": "Dirección", "tipo": "texto", "req": True, "max": 150},
            {"k": "comuna", "t": "Comuna", "tipo": "select", "req": True, "opciones": COMUNAS_COQUIMBO},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("codigo", "Código"), ("nombre", "Nombre"), ("direccion", "Dirección"), ("comuna", "Comuna"), ("estado", "Estado")],
    },
    "roles": {
        "titulo": "Roles y permisos", "migas": "Roles", "singular": "rol", "genero": "m",
        "columnas": [
            {"k": "codigo", "t": "Código", "sort": "codigo"},
            {"k": "nombre", "t": "Rol", "sort": "nombre"},
            {"k": "alcance_texto", "t": "Alcance", "sort": "alcance"},
            {"k": "permisos", "t": "Permisos", "fmt": "cuenta"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "codigo", "t": "Código", "tipo": "texto", "req": True, "max": 20, "mayus": True, "ayuda": "Ej.: ROL05."},
            {"k": "nombre", "t": "Nombre del rol", "tipo": "texto", "req": True, "max": 60},
            {"k": "descripcion", "t": "Descripción", "tipo": "area", "max": 255},
            {"k": "alcance", "t": "Alcance autorizado", "tipo": "select", "req": True,
             "opciones_kv": [[k, v] for k, v in ALCANCE_TEXTO.items()],
             "ayuda": "Define cuántas delegaciones puede operar quien tenga este rol."},
            {"k": "permisos", "t": "Permisos", "tipo": "permisos", "req": True},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("codigo", "Código"), ("nombre", "Rol"), ("descripcion", "Descripción"), ("alcance_texto", "Alcance"),
                  ("n_usuarios", "Usuarios con este rol"), ("estado", "Estado"), ("permisos", "Permisos")],
    },
    "usuarios": {
        "titulo": "Usuarios del sistema", "migas": "Usuarios", "singular": "usuario", "genero": "m",
        "columnas": [
            {"k": "nombre", "t": "Nombre", "sort": "nombre"},
            {"k": "correo", "t": "Correo", "sort": "correo"},
            {"k": "rol", "t": "Rol", "sort": "rol"},
            {"k": "delegaciones_texto", "t": "Delegación"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "usuario", "t": "Nombre de usuario", "tipo": "texto", "req": True, "max": 30,
             "ayuda": "Minúsculas, números, punto o guion. Sirve para iniciar sesión."},
            {"k": "nombre", "t": "Nombre completo", "tipo": "texto", "req": True, "max": 100},
            {"k": "correo", "t": "Correo electrónico", "tipo": "email", "req": True, "max": 120},
            {"k": "rol_id", "t": "Rol", "tipo": "select_remoto", "req": True, "url": "/api/opciones/roles"},
            {"k": "delegaciones_ids", "t": "Delegaciones autorizadas", "tipo": "checks_remoto", "req": True,
             "url": "/api/opciones/delegaciones", "ayuda": "Si el rol permite una sola delegación, marca solo una."},
            {"k": "password", "t": "Contraseña", "tipo": "password", "max": 128, "req_crear": True,
             "ayuda": "Mínimo 10 caracteres con mayúscula, minúscula, número y símbolo. "
                      "Al editar, déjala vacía para conservar la actual."},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("usuario", "Usuario"), ("nombre", "Nombre"), ("correo", "Correo"), ("rol", "Rol"),
                  ("delegaciones_texto", "Delegaciones"), ("estado", "Estado")],
        "ambito": True,
    },
    "items": {
        "titulo": "Ítems y metas", "migas": "Ítems y metas", "singular": "ítem", "genero": "m",
        "columnas": [
            {"k": "codigo", "t": "Código", "sort": "codigo"},
            {"k": "nombre", "t": "Nombre", "sort": "nombre"},
            {"k": "descripcion", "t": "Descripción"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "codigo", "t": "Código", "tipo": "texto", "req": True, "max": 20, "mayus": True, "ayuda": "Ej.: IT001."},
            {"k": "nombre", "t": "Nombre", "tipo": "texto", "req": True, "max": 100},
            {"k": "descripcion", "t": "Descripción", "tipo": "area", "max": 255},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("codigo", "Código"), ("nombre", "Nombre"), ("descripcion", "Descripción"), ("estado", "Estado")],
    },
    "tipos": {
        "titulo": "Tipos de Atención", "migas": "Tipo de Atención", "singular": "tipo de atención", "genero": "m",
        "columnas": [
            {"k": "codigo", "t": "Código", "sort": "codigo"},
            {"k": "nombre", "t": "Nombre", "sort": "nombre"},
            {"k": "descripcion", "t": "Descripción"},
            {"k": "n_subs", "t": "Subatenciones"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "codigo", "t": "Código", "tipo": "texto", "req": True, "max": 20, "mayus": True, "ayuda": "Ej.: TA001."},
            {"k": "nombre", "t": "Nombre", "tipo": "texto", "req": True, "max": 60},
            {"k": "descripcion", "t": "Descripción", "tipo": "area", "max": 255},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("codigo", "Código"), ("nombre", "Nombre"), ("descripcion", "Descripción"),
                  ("n_subs", "Subatenciones asociadas"), ("estado", "Estado")],
    },
    "subtipos": {
        "titulo": "Sub Atención", "migas": "Sub Atención", "singular": "subatención", "genero": "f",
        "columnas": [
            {"k": "codigo", "t": "Código", "sort": "codigo"},
            {"k": "nombre", "t": "Nombre", "sort": "nombre"},
            {"k": "tipo_nombre", "t": "Tipo asociado", "sort": "tipo"},
            {"k": "estado", "t": "Estado", "sort": "estado", "fmt": "estado"},
        ],
        "campos": [
            {"k": "codigo", "t": "Código", "tipo": "texto", "req": True, "max": 20, "mayus": True, "ayuda": "Ej.: SA001."},
            {"k": "nombre", "t": "Nombre", "tipo": "texto", "req": True, "max": 80},
            {"k": "tipo_id", "t": "Tipo de Atención", "tipo": "select_remoto", "req": True, "url": "/api/opciones/tipos"},
            {"k": "activo", "t": "Estado", "tipo": "estado"},
        ],
        "vista": [("codigo", "Código"), ("nombre", "Nombre"), ("tipo_nombre", "Tipo de Atención"),
                  ("n_atenciones", "Atenciones registradas"), ("estado", "Estado")],
    },
}

ATENCIONES_LISTA = {
    "titulo": "Atenciones registradas", "singular": "atención", "genero": "f", "solo_lectura": True,
    "columnas": [
        {"k": "folio", "t": "Folio", "sort": "folio"},
        {"k": "fecha", "t": "Fecha y hora", "sort": "fecha"},
        {"k": "solicitante", "t": "Solicitante", "sort": "solicitante"},
        {"k": "tipo", "t": "Tipo", "sort": "tipo"},
        {"k": "subtipo", "t": "Sub Atención", "sort": "subtipo"},
        {"k": "responsable", "t": "Responsable"},
    ],
    "campos": [],
    "vista": [("folio", "Folio"), ("fecha", "Fecha y hora"), ("solicitante", "Solicitante"), ("rut", "RUT"),
              ("tipo", "Tipo de Atención"), ("subtipo", "Sub Atención"), ("delegacion", "Delegación"),
              ("responsable", "Responsable"), ("descripcion", "Descripción")],
    "ambito": True,
}

# Plantillas de módulos pendientes: solo demuestran navegación y visibilidad por rol.
PENDIENTES = {
    "vecinos": {
        "titulo": "Vecinos", "ruta": "/vecinos",
        "descripcion": "Catálogo de solicitantes: alta, edición, historial de atenciones y datos de contacto.",
        "nota": "En esta entrega el ingreso de atención ya permite buscar un solicitante y registrar uno nuevo "
                "desde el formulario. La administración completa del catálogo queda para la siguiente etapa.",
        "columnas": ["RUT", "Nombre", "Comuna", "Atenciones"],
        "filas": [["12.345.678-5", "Persona de ejemplo A", "La Serena", "3"],
                  ["9.876.543-3", "Persona de ejemplo B", "La Serena", "1"],
                  ["15.000.000-K", "Persona de ejemplo C", "La Serena", "0"]],
    },
    "gestion_tipos": {
        "titulo": "Tipos de Gestión", "ruta": "/tipos-gestion",
        "descripcion": "Catálogo de gestiones que se pueden realizar sobre una atención (derivar, resolver, cerrar).",
        "nota": "Se incluye como contexto del modelo de datos; no es requisito funcional de esta entrega.",
        "columnas": ["Código", "Nombre", "Plazo referencial", "Estado"],
        "filas": [["TG01", "Derivación", "5 días", "Activo"], ["TG02", "Resolución directa", "2 días", "Activo"],
                  ["TG03", "Cierre", "—", "Activo"]],
    },
    "seguimiento": {
        "titulo": "Seguimiento de casos", "ruta": "/seguimiento",
        "descripcion": "Bandeja para dar seguimiento a las atenciones abiertas de la delegación.",
        "nota": "Pendiente de definición funcional con el equipo de Backend.",
        "columnas": ["Folio", "Solicitante", "Estado", "Último movimiento"],
        "filas": [["ATN-0000-000001", "Persona de ejemplo A", "En proceso", "Hace 2 días"],
                  ["ATN-0000-000002", "Persona de ejemplo B", "Derivada", "Hace 5 días"]],
    },
    "reportes": {
        "titulo": "Reportes", "ruta": "/reportes",
        "descripcion": "Indicadores de cobertura, satisfacción y tiempos de respuesta por delegación.",
        "nota": "Se alimentará con el mantenedor de Ítems y metas cuando exista información histórica.",
        "columnas": ["Indicador", "Meta", "Resultado", "Delegación"],
        "filas": [["Cobertura", "90 %", "—", "Todas"], ["Satisfacción", "85 %", "—", "Todas"], ["Tiempos", "48 h", "—", "Todas"]],
    },
}
