# SGR · Gestión de Atención Ciudadana · Municipalidad de La Serena

Proyecto Integrado · **Segunda evaluación**. Versión de la entrega: `2.0.0-entrega2` (archivo `VERSION`; se muestra en el pie y en `/salud`).

**Integrantes:** _(completar)_ · **Docente:** _(completar)_ · **Repositorio:** _(URL)_ · **URL AWS:** _(URL)_ · **Commit/etiqueta entregado:** _(completar)_

## Qué incluye

Login · recuperación de contraseña en 3 pasos (solicitar, validar código, nueva clave) · seis mantenedores (Delegaciones, Roles, Usuarios, Ítems y metas, Tipo de Atención, Sub Atención) · ingreso de atención · menú y pantallas diferenciadas por rol · plantillas de los módulos pendientes · exportación a Excel · SweetAlert2 en alertas y confirmaciones · pruebas funcionales automáticas y script de estrés.

## Requisitos
Python 3.12+ (probado con 3.12). Dependencias en `requirements.txt` (Flask, openpyxl, gunicorn). Conexión a Internet en el navegador para cargar SweetAlert2 desde jsDelivr.

## Instalación y ejecución local
```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                     # opcional; define variables de entorno si lo usas
python manage.py init-db --demo --volumen 60             # crea instance/sgr.sqlite3 con datos ficticios
python manage.py run                                     # http://localhost:5000
```
Sin `SECRET_KEY` el modo desarrollo genera una clave efímera; en producción es obligatoria (`APP_ENV=production`).

### Cuentas de demostración (datos ficticios)
Contraseña de todas: `Demo#2026Sgr!` — **cámbienla o elimínenlas antes de usar datos reales.**

| Usuario | Rol | Delegaciones |
|---|---|---|
| `superadmin` | Superadministrador | todas |
| `coordinador` | Coordinador | DEL01, DEL02 |
| `delegado` / `delegado2` | Delegado municipal | DEL01 / DEL02 |
| `funcionario` / `funcionario2` | Funcionario | DEL01 / DEL02 |
| `inactivo` | (cuenta inactiva, para pruebas) | DEL01 |

Qué ve y puede hacer cada rol: `docs/MATRIZ_PERMISOS.md`.

### Probar la recuperación de contraseña sin correo real
Con `MAIL_MODE=console` (por defecto) el correo es **simulado**: el código aparece en `/dev/bandeja` (enlace en el paso 2). Desactiven esa bandeja con `DEV_OUTBOX=0` cuando configuren SMTP.

## Configuración
Todo por variables de entorno (ver `.env.example`): base de datos, vigencia del código (10 min), espera de reenvío (45 s), intentos máximos, bloqueo de login, SMTP. **No suban `.env` ni claves al repositorio** (ya está en `.gitignore`).

## Base de datos
`db/schema.sql` (migración inicial) y `app/seed.py` (roles, delegaciones y datos de demostración). `python manage.py init-db` (sin `--demo`) crea solo esquema, roles y delegaciones; `python manage.py crear-superadmin` crea el primer administrador.

## Pruebas
```bash
python tests/run_tests.py                 # 66 pruebas funcionales; guarda evidencia en evidencias/
python tests/ui_smoke.py http://localhost:5000   # humo de interfaz con Playwright (servidor encendido)
python tests/stress/stress_test.py --base https://TU-DOMINIO --clave '...'   # estrés (ver docs/RESULTADOS_ESTRES.md)
```
Plan y registro: `docs/PLAN_PRUEBAS.md`.

## Despliegue en AWS
`docs/DESPLIEGUE_AWS.md` y carpeta `deploy/` (EC2 + nginx + gunicorn + systemd).

## Estado de cada módulo

| Módulo / función | Estado | Observaciones |
|---|---|---|
| Login, cierre de sesión, rutas protegidas | **Operativo** | Bloqueo tras 5 intentos fallidos; mensajes genéricos |
| Recuperación de contraseña (3 pasos) | **Operativo** | El **envío de correo es simulado** por defecto (bandeja de desarrollo); SMTP real configurable y sin probar |
| CRUD Delegaciones, Roles, Usuarios, Ítems y metas, Tipo y Sub Atención | **Operativo** | Persisten en SQLite; reglas de integridad en servidor |
| Tablas: búsqueda, paginación, filtros, orden | **Operativo** | Búsqueda sin mayúsculas ni tildes, en varios campos |
| Exportar a Excel | **Operativo** | Todas las páginas del filtro; sin campos sensibles |
| Ingreso de atención | **Operativo** | Delegación, responsable y fecha las fija el servidor; folio `ATN-AAAA-NNNNNN` |
| Catálogo de Vecinos | **Parcial** | Búsqueda y alta rápida desde el formulario; CRUD completo pendiente |
| Roles/permisos y delegación activa | **Operativo** | Validados en el servidor |
| Vecinos, Tipos de Gestión, Seguimiento, Reportes | **Plantilla (pendiente)** | Solo navegación y visibilidad por rol; datos ficticios, sin lógica |
| Normas gráficas oficiales | **Parcial** | Rojo institucional `#920000`; **logotipo y tipografía oficiales por incorporar** (ver abajo) |
| SweetAlert2 | **Implementado** | Verificado solo con respaldo nativo (entorno sin Internet); probar con la librería real |
| Despliegue AWS, repositorio Git, estrés en AWS | **Pendiente (equipo)** | Scripts y guías incluidos |

## Identidad visual: pendiente de completar
1. Descarguen el material oficial de https://laserena.cl/conocenos/normas-graficas.
2. Reemplacen `app/static/img/logo-laserena.svg` (hoy es un marcador) respetando versiones y áreas de resguardo.
3. Ajusten colores y tipografía en las variables al inicio de `app/static/css/sgr.css` (`--rojo`, `--fuente`, …).

## Seguridad (resumen)
Contraseñas con hash scrypt · códigos de recuperación guardados solo como hash, vigencia, un solo uso e intentos limitados · respuesta de recuperación que no revela si el correo existe · CSRF en toda escritura · sesión HttpOnly/SameSite · permisos y delegación validados en cada solicitud · cabeceras de seguridad y CSP · exportaciones con neutralización de fórmulas.

## Estructura
```
app/            código (Flask): rutas, motor CRUD, reglas, plantillas, estáticos
db/schema.sql   esquema de base de datos
deploy/         nginx, gunicorn, scripts de instalación/actualización en EC2
docs/           análisis, plan de pruebas, matriz de permisos, AWS, estrés
tests/          pruebas automáticas, humo de interfaz, estrés
evidencias/     resultados y capturas generados por las pruebas
manage.py       utilidades (init-db, crear-superadmin, run)
```
