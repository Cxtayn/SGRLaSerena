-- SGR · Esquema de base de datos (SQLite). Migración inicial 001.
-- Las tablas usan SQL estándar para facilitar el paso a MySQL/PostgreSQL (RDS).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS delegaciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    direccion   TEXT NOT NULL,
    comuna      TEXT NOT NULL,
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS roles (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL DEFAULT '',
    alcance     TEXT NOT NULL CHECK (alcance IN ('TODAS','ASIGNADAS','UNA')),
    permisos    TEXT NOT NULL DEFAULT '[]',          -- JSON: ["modulo:accion", ...]
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS usuarios (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario          TEXT NOT NULL UNIQUE,
    nombre           TEXT NOT NULL,
    correo           TEXT NOT NULL UNIQUE,
    password_hash    TEXT NOT NULL,
    rol_id           INTEGER NOT NULL REFERENCES roles(id),
    activo           INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    session_version  INTEGER NOT NULL DEFAULT 1,     -- se incrementa al cambiar la clave
    ultima_delegacion_id INTEGER REFERENCES delegaciones(id),
    creado_en        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS usuario_delegacion (
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    delegacion_id INTEGER NOT NULL REFERENCES delegaciones(id),
    PRIMARY KEY (usuario_id, delegacion_id)
);

CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS tipos_atencion (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL UNIQUE,
    descripcion TEXT NOT NULL DEFAULT '',
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS subatenciones (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo      TEXT NOT NULL UNIQUE,
    nombre      TEXT NOT NULL,
    tipo_id     INTEGER NOT NULL REFERENCES tipos_atencion(id),
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE (tipo_id, nombre)
);

-- Solicitantes (catálogo de Vecinos). En esta entrega solo búsqueda y alta rápida.
CREATE TABLE IF NOT EXISTS vecinos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    rut         TEXT NOT NULL UNIQUE,                 -- normalizado: 12345678-5
    nombres     TEXT NOT NULL,
    apellidos   TEXT NOT NULL,
    correo      TEXT,
    telefono    TEXT,
    activo      INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    creado_en   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);

CREATE TABLE IF NOT EXISTS atenciones (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    folio           TEXT UNIQUE,                      -- ATN-AAAA-000001
    vecino_id       INTEGER NOT NULL REFERENCES vecinos(id),
    tipo_id         INTEGER NOT NULL REFERENCES tipos_atencion(id),
    subtipo_id      INTEGER NOT NULL REFERENCES subatenciones(id),
    descripcion     TEXT NOT NULL,
    delegacion_id   INTEGER NOT NULL REFERENCES delegaciones(id),
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id),
    token_envio     TEXT UNIQUE,                      -- evita doble envío
    fecha_registro  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS ix_atenciones_deleg_fecha ON atenciones (delegacion_id, fecha_registro DESC);

-- Recuperación de contraseña: el código nunca se guarda en claro.
CREATE TABLE IF NOT EXISTS recuperaciones (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id    INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    codigo_hash   TEXT NOT NULL,
    expira_en     TEXT NOT NULL,
    intentos      INTEGER NOT NULL DEFAULT 0,
    usado         INTEGER NOT NULL DEFAULT 0,
    verificado    INTEGER NOT NULL DEFAULT 0,
    token_hash    TEXT,                               -- token de la etapa 3
    token_expira  TEXT,
    creado_en     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_recup_usuario ON recuperaciones (usuario_id, creado_en DESC);

-- Intentos de login por identificador (existente o no) para no revelar cuentas.
CREATE TABLE IF NOT EXISTS intentos_login (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    identificador TEXT NOT NULL,
    creado_en     TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_intentos_ident ON intentos_login (identificador, creado_en);

-- Solo desarrollo: correos simulados (MAIL_MODE=console).
CREATE TABLE IF NOT EXISTS bandeja_dev (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    destino     TEXT NOT NULL,
    asunto      TEXT NOT NULL,
    cuerpo      TEXT NOT NULL,
    creado_en   TEXT NOT NULL
);
