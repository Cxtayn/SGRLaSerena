# Análisis de requisitos · SGR · Segunda evaluación

Fuente: `Requisitos_Segunda_Evaluacion_SGR.pdf` (secciones A1–A4 y diseños C1–C6).

## 1. Qué pide la entrega

Una aplicación web con **acceso (login)**, **recuperación de contraseña en 3 pasos**, **seis mantenedores** y el **ingreso de atención ciudadana**, todo con el mismo template institucional, identificando siempre la **delegación activa** según el perfil, **desplegada en AWS** y con el código en un **repositorio Git**. Además: pruebas funcionales y de estrés documentadas, SweetAlert2 en todas las alertas y demostración de **roles y permisos** (requisito «fundamental»).

## 2. Decisiones de diseño (el PDF no las fija)

| Tema | Decisión | Motivo |
|---|---|---|
| Stack | Python 3.12 + Flask, SQLite, HTML/CSS/JS sin build | Sin dependencias pesadas, fácil de desplegar en una sola EC2 y de explicar en la defensa. |
| Base de datos | SQLite (archivo en el volumen EBS) | Suficiente para la entrega; el esquema es SQL estándar para migrar a RDS. **Cambiar a RDS exigiría adaptar `app/db.py`.** |
| Roles | Superadministrador, Coordinador, Delegado municipal, Funcionario (los del ejemplo del PDF) | Cada rol tiene **alcance** (todas / asignadas / una delegación) y **permisos** por módulo y acción. |
| Usuario de login | Se agregó el campo `usuario` | El login pide «usuario o correo»; el modelo del PDF solo lista correo. |
| Solicitante | Tabla `vecinos` con búsqueda y **alta rápida** desde el formulario | El PDF pide identificar al solicitante «según el modelo definido»; el CRUD completo de Vecinos queda fuera. |
| Correo | `MAIL_MODE=console` (simulado) o `smtp` | Permite demostrar el flujo sin infraestructura de correo; en AWS se usa SES por SMTP. |
| Valores referenciales | Vigencia 10 min, reenvío 45 s, 5 intentos | Del PDF; configurables en `.env`. |
| Alertas | SweetAlert2 11.12.4 desde CDN (jsDelivr) | Exigido. Respaldo con diálogos nativos si el CDN no responde. |

## 3. Trazabilidad requisito → implementación

| Requisito (PDF) | Dónde está | Estado |
|---|---|---|
| Login usuario/correo + validación + acceso por perfil | `routes_auth.py`, `login.html`, `security.py` | Operativo, probado |
| Recuperar contraseña: solicitar, validar (vigencia, reenvío, intentos), nueva clave, volver al login | `routes_auth.py`, `recuperar/validar/nueva.html`, `auth.js` | Operativo, probado (correo simulado) |
| 6 CRUD (Delegaciones, Roles, Usuarios, Ítems y metas, Tipo, Sub Atención) | `engine.py`, `resources.py`, `crud.js`, `ui_config.py` | Operativo, probado |
| Tabla, paginador, total, búsqueda parcial sin mayúsculas, filtros conservados | `engine.py` (`norm()` sin tildes), `crud.js` (estado en la URL) | Operativo, probado |
| Estados de carga, vacío, sin coincidencias, error | `crud.js` | Operativo (revisado en navegador) |
| Exportar a Excel (filtro aplicado, todas las páginas, sin campos internos) | `engine.exportar`, hoja «Filtro aplicado» | Operativo, probado |
| Ingreso de atención con Tipo→Sub dependiente, delegación del contexto, responsable y fecha automáticos, folio, sin doble envío | `resources.crear_atencion`, `atencion.js` | Operativo, probado |
| Distintivo de delegación (texto + icono), usuario y rol; selector solo con delegaciones autorizadas; aviso de cambios sin guardar | `base.html`, `app.js`, `/api/contexto` | Operativo (aviso: verificar manualmente, MAN-08) |
| Validación en servidor del alcance y permisos | `security.py`, `engine.py`, `resources.py` | Operativo, probado |
| Interfaz por rol (menú y módulos) + plantillas de módulos pendientes | `base.html`, `pendiente.html`, `ui_config.PENDIENTES` | Operativo |
| Normas gráficas oficiales (logotipo, colores, tipografías) | `static/css/sgr.css` (tokens), `static/img/logo-laserena.svg` | **Parcial:** ver sección 5 |
| SweetAlert2 en alertas, confirmaciones y resultados | `app.js` (`SGR.msg`) | Implementado; **no verificado con la librería real** (sin Internet en el entorno de desarrollo) |
| Despliegue AWS + URL + acceso de evaluación | `deploy/`, `docs/DESPLIEGUE_AWS.md` | **Pendiente (lo realiza el equipo)** |
| Repositorio Git con historial y etiqueta | — | **Pendiente (lo realiza el equipo)** |
| README, migraciones/scripts BD, ejemplo de configuración | `README.md`, `db/schema.sql`, `.env.example` | Entregado (completar integrantes) |
| Pruebas funcionales y de estrés documentadas | `docs/PLAN_PRUEBAS.md`, `tests/` | Funcionales automáticas: hechas. Estrés en AWS: **pendiente** |
| Resumen operativo / simulado / pendiente | `README.md` §Estado | Entregado |

## 4. Riesgos y puntos de atención para la defensa

1. **Normas gráficas.** El sitio de la municipalidad carga su contenido dinámicamente y no pude leer el manual desde el entorno de desarrollo. Solo se verificó el rojo `#920000` (color de tema del portal). **Deben descargar el manual oficial, poner el logotipo real en `static/img/logo-laserena.svg` y ajustar tipografía/colores en las variables de `sgr.css`.**
2. **Demostrar «operativo» vs «simulado».** Correo simulado, catálogo de Vecinos parcial y módulos-plantilla están rotulados como tales en la interfaz y en el README.
3. **Roles y permisos** se demuestran con 4 cuentas demo (ver `MATRIZ_PERMISOS.md`).
4. **Secretos:** `SECRET_KEY` y SMTP solo por variables de entorno; las cuentas demo tienen clave pública: cámbienla o elimínenlas antes de usar datos reales.
5. **SQLite** limita la escritura concurrente; sirve para la prueba de estrés de esta entrega, y conviene mencionarlo como límite conocido.

## 5. Qué queda en manos del equipo

AWS (EC2/dominio/HTTPS), repositorio Git, logotipo y tipografía oficiales, prueba de estrés en AWS, ejecución de los casos manuales, nombres de integrantes y responsables en los documentos.
