"""Datos base y de prueba. TODOS los datos de demostración son ficticios.
Las contraseñas de las cuentas demo son públicas (están en el README): cámbielas o
elimine las cuentas antes de usar el sistema con datos reales."""
import json
import random

from werkzeug.security import generate_password_hash

from .db import ahora_iso
from .permisos import TODOS_LOS_PERMISOS

PASSWORD_DEMO = "Demo#2026Sgr!"


def _crud(mod, *acc):
    return [f"{mod}:{a}" for a in acc]


ROLES = [
    ("ROL01", "Superadministrador", "Administra todo el sistema y todas las delegaciones.", "TODAS", sorted(TODOS_LOS_PERMISOS)),
    ("ROL02", "Coordinador", "Coordina varias delegaciones: usuarios, catálogos y atenciones.", "ASIGNADAS",
     _crud("delegaciones", "ver", "exportar") + _crud("usuarios", "ver", "crear", "editar", "exportar")
     + _crud("items", "ver", "crear", "editar", "exportar") + _crud("tipos", "ver", "crear", "editar", "exportar")
     + _crud("subtipos", "ver", "crear", "editar", "exportar") + _crud("atenciones", "ver", "crear", "exportar")
     + ["vecinos:ver", "gestion_tipos:ver", "seguimiento:ver", "reportes:ver", "inicio:ver"]),
    ("ROL03", "Delegado municipal", "Responsable de una delegación: consulta catálogos y usuarios, gestiona atenciones.", "UNA",
     _crud("delegaciones", "ver") + _crud("usuarios", "ver", "exportar") + _crud("items", "ver") + _crud("tipos", "ver")
     + _crud("subtipos", "ver") + _crud("atenciones", "ver", "crear", "exportar")
     + ["vecinos:ver", "seguimiento:ver", "reportes:ver", "inicio:ver"]),
    ("ROL04", "Funcionario", "Registra y consulta atenciones de su delegación.", "UNA",
     _crud("atenciones", "ver", "crear") + ["vecinos:ver", "seguimiento:ver", "inicio:ver"]),
]

DELEGACIONES = [
    ("DEL01", "Centro", "Av. Ejemplo 100"), ("DEL02", "Norte", "Calle Ejemplo 200"), ("DEL03", "Sur", "Calle Ejemplo 300"),
    ("DEL04", "Las Compañías", "Av. Ejemplo 400"), ("DEL05", "La Pampa", "Calle Ejemplo 500"),
    ("DEL06", "La Antena", "Pasaje Ejemplo 600"), ("DEL07", "Costanera", "Av. Ejemplo 700"), ("DEL08", "Rural", "Camino Ejemplo 800"),
]

TIPOS = {
    ("TA001", "Social", "Apoyo social"): [("SA001", "Ayuda social"), ("SA002", "Subsidio de agua"), ("SA003", "Canasta de emergencia")],
    ("TA002", "Salud", "Orientación"): [("SA004", "Consulta médica"), ("SA005", "Operativo de salud"), ("SA006", "Entrega de insumos")],
    ("TA003", "Educación", "Apoyo escolar"): [("SA007", "Beca municipal"), ("SA008", "Útiles escolares")],
    ("TA004", "Vivienda", "Orientación habitacional"): [("SA009", "Postulación a subsidio"), ("SA010", "Mejoramiento de vivienda")],
    ("TA005", "Seguridad", "Prevención y denuncias"): [("SA011", "Alarma comunitaria"), ("SA012", "Iluminación y espacios públicos")],
}

ITEMS_BASE = [("IT001", "Cobertura", "Atenciones"), ("IT002", "Satisfacción", "Experiencia"), ("IT003", "Tiempos", "Respuesta"),
              ("IT004", "Resolución", "Casos resueltos"), ("IT005", "Derivaciones", "Casos derivados"), ("IT006", "Reclamos", "Reclamos recibidos")]

NOMBRES = ["Camila", "Matías", "Valentina", "Benjamín", "Sofía", "Joaquín", "Isidora", "Tomás", "Fernanda", "Diego",
           "Javiera", "Nicolás", "Constanza", "Felipe", "Antonia"]
APELLIDOS = ["Ejemplo", "Prueba", "Demo", "Muestra", "Ficticio", "Simulado", "Modelo", "Piloto"]


def _dv(cuerpo):
    suma, factor = 0, 2
    for d in reversed(str(cuerpo)):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    r = 11 - (suma % 11)
    return "0" if r == 11 else "K" if r == 10 else str(r)


def cargar_semilla(conn, demo=True, volumen=0):
    cur = conn.cursor()
    if cur.execute("SELECT COUNT(*) FROM roles").fetchone()[0] == 0:
        for cod, nombre, desc, alcance, permisos in ROLES:
            cur.execute("INSERT INTO roles (codigo,nombre,descripcion,alcance,permisos) VALUES (?,?,?,?,?)",
                        (cod, nombre, desc, alcance, json.dumps(sorted(set(permisos)))))
        for cod, nom, dire in DELEGACIONES:
            cur.execute("INSERT INTO delegaciones (codigo,nombre,direccion,comuna) VALUES (?,?,?,?)", (cod, nom, dire, "La Serena"))
        conn.commit()
    if not demo:
        return
    if cur.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        h = generate_password_hash(PASSWORD_DEMO)
        rol = {r["codigo"]: r["id"] for r in cur.execute("SELECT id, codigo FROM roles")}
        deleg = {d["codigo"]: d["id"] for d in cur.execute("SELECT id, codigo FROM delegaciones")}
        usuarios = [
            ("superadmin", "Sara Superadmin (ejemplo)", "admin@example.test", "ROL01", ["DEL01"], 1),
            ("coordinador", "Carlos Coordinador (ejemplo)", "coordinador@example.test", "ROL02", ["DEL01", "DEL02"], 1),
            ("delegado", "Daniela Delegada (ejemplo)", "delegado@example.test", "ROL03", ["DEL01"], 1),
            ("delegado2", "Diego Delegado Norte (ejemplo)", "delegado2@example.test", "ROL03", ["DEL02"], 1),
            ("funcionario", "Ana Funcionaria (ejemplo)", "funcionario@example.test", "ROL04", ["DEL01"], 1),
            ("funcionario2", "Luis Funcionario Norte (ejemplo)", "funcionario2@example.test", "ROL04", ["DEL02"], 1),
            ("inactivo", "Irene Inactiva (ejemplo)", "inactivo@example.test", "ROL04", ["DEL01"], 0),
        ]
        for u, nombre, correo, r, ds, activo in usuarios:
            cur.execute("INSERT INTO usuarios (usuario,nombre,correo,password_hash,rol_id,activo,ultima_delegacion_id) VALUES (?,?,?,?,?,?,?)",
                        (u, nombre, correo, h, rol[r], activo, deleg[ds[0]]))
            uid = cur.lastrowid
            for d in ds:
                cur.execute("INSERT INTO usuario_delegacion VALUES (?,?)", (uid, deleg[d]))
        conn.commit()
    if cur.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 0:
        for cod, nom, desc in ITEMS_BASE:
            cur.execute("INSERT INTO items (codigo,nombre,descripcion) VALUES (?,?,?)", (cod, nom, desc))
        for i in range(len(ITEMS_BASE) + 1, 25):
            cur.execute("INSERT INTO items (codigo,nombre,descripcion,activo) VALUES (?,?,?,?)",
                        (f"IT{i:03d}", f"Meta de ejemplo {i:02d}", "Dato ficticio para probar paginación", 1 if i % 7 else 0))
        for (cod, nom, desc), subs in TIPOS.items():
            cur.execute("INSERT INTO tipos_atencion (codigo,nombre,descripcion) VALUES (?,?,?)", (cod, nom, desc))
            tid = cur.lastrowid
            for scod, snom in subs:
                cur.execute("INSERT INTO subatenciones (codigo,nombre,tipo_id) VALUES (?,?,?)", (scod, snom, tid))
        conn.commit()
    if cur.execute("SELECT COUNT(*) FROM vecinos").fetchone()[0] == 0:
        rnd = random.Random(2026)
        for i in range(30):
            cuerpo = 10_000_000 + i * 317_531
            cur.execute("INSERT INTO vecinos (rut,nombres,apellidos,correo) VALUES (?,?,?,?)",
                        (f"{cuerpo}-{_dv(cuerpo)}", NOMBRES[i % len(NOMBRES)], f"{APELLIDOS[i % len(APELLIDOS)]} {APELLIDOS[(i * 3 + 1) % len(APELLIDOS)]}",
                         f"vecino{i + 1}@example.test"))
        conn.commit()
    if volumen > 0:
        rnd = random.Random(7)
        vec = [r[0] for r in cur.execute("SELECT id FROM vecinos")]
        deleg = [r[0] for r in cur.execute("SELECT id FROM delegaciones WHERE activo=1")]
        users = [r[0] for r in cur.execute("SELECT id FROM usuarios WHERE activo=1")]
        subs = cur.execute("SELECT id, tipo_id FROM subatenciones WHERE activo=1").fetchall()
        base = cur.execute("SELECT COALESCE(MAX(id),0) FROM atenciones").fetchone()[0]
        ahora = ahora_iso()
        for i in range(volumen):
            s = rnd.choice(subs)
            cur.execute("INSERT INTO atenciones (folio,vecino_id,tipo_id,subtipo_id,descripcion,delegacion_id,usuario_id,fecha_registro) "
                        "VALUES (?,?,?,?,?,?,?,?)",
                        (f"ATN-{ahora[:4]}-{base + i + 1:06d}", rnd.choice(vec), s["tipo_id"], s["id"],
                         f"Atención de prueba número {base + i + 1} generada para carga.", rnd.choice(deleg), rnd.choice(users),
                         f"{ahora[:4]}-{rnd.randint(1, 9):02d}-{rnd.randint(1, 28):02d}T{rnd.randint(11, 22):02d}:{rnd.randint(0, 59):02d}:00Z"))
        conn.commit()
