# Matriz de roles y permisos (cuentas demo)

Contraseña de todas las cuentas demo: ver README. Correos y usuarios son ficticios.

| Rol | Cuenta demo | Alcance | Delegaciones |
|---|---|---|---|
| Superadministrador | `superadmin` | Todas | Cualquiera (selector con las 8) |
| Coordinador | `coordinador` | Asignadas | DEL01 y DEL02 (selector) |
| Delegado municipal | `delegado` (DEL01), `delegado2` (DEL02) | Una | Fija |
| Funcionario | `funcionario` (DEL01), `funcionario2` (DEL02) | Una | Fija |
| (Cuenta inactiva) | `inactivo` | — | Sirve para probar el rechazo de cuentas inactivas |

Permisos por módulo (V = ver, C = crear, E = editar, X = eliminar, P = exportar):

| Módulo | Superadmin | Coordinador | Delegado | Funcionario |
|---|---|---|---|---|
| Delegaciones | VCEXP | V P | V | — |
| Roles | VCEXP | — | — | — |
| Usuarios | VCEXP | V C E P | V P | — |
| Ítems y metas | VCEXP | V C E P | V | — |
| Tipo de Atención | VCEXP | V C E P | V | — |
| Sub Atención | VCEXP | V C E P | V | — |
| Atenciones | V C P | V C P | V C P | V C |
| Vecinos (plantilla) | V | V | V | V |
| Tipos de Gestión (plantilla) | V | V | — | — |
| Seguimiento (plantilla) | V | V | V | V |
| Reportes (plantilla) | V | V | V | — |

Reglas adicionales aplicadas **en el servidor**:
- Un usuario solo ve/edita usuarios que comparten alguna de sus delegaciones; las demás responden 403.
- Un rol solo puede asignar delegaciones propias y roles de alcance y permisos no superiores a los suyos.
- Nadie puede cambiar su propio rol, desactivarse o eliminarse; siempre debe quedar un superadministrador activo.
- Los permisos de un rol son editables en Roles (matriz); los cambios rigen de inmediato, porque cada solicitud los lee de la base.
- Para recrear estos permisos de forma exacta, los roles iniciales están en `app/seed.py`.
