# Plan y registro de pruebas · SGR · Segunda evaluación

Este documento cumple lo pedido en la sección A3 del documento de requisitos. Las columnas «Requisito» indican el
número de la lista de verificación de la sección A4 (1 = login y recuperación, 2 = seis CRUD, 3 = ingreso de atención,
4 = tabla/paginador/búsqueda/Excel, 5 = normas gráficas, delegación y perfil, 6 = validaciones y SweetAlert2,
7 = AWS/Git, 8 = pruebas, 9 = resumen de estado).

## 1. Alcance, entorno y criterios

- **Entorno de las pruebas automáticas:** local (Python 3.12, SQLite temporal con datos de demostración, cliente de pruebas de Flask). Cubren la **lógica del servidor**: validaciones, permisos, alcance por delegación, reglas de negocio y exportación.
- **Entorno pendiente:** AWS (ver `docs/DESPLIEGUE_AWS.md`). Los casos manuales de abajo y la prueba de estrés deben repetirse allí.
- **Datos de prueba:** cuentas demo del README (todas ficticias). Contraseña común de demo: la indicada en el README.
- **Criterio de aprobación:** el resultado obtenido coincide con el esperado; un caso solo se declara *Aprobada* si se ejecutó. Lo no ejecutado queda *Pendiente* con su justificación.
- **Defectos:** se registran en la sección 5 y se repite la prueba tras corregir.

## 2. Pruebas funcionales automáticas

**Precondiciones comunes:** base creada con `python manage.py init-db --demo --volumen 60` (en las pruebas se crea una BD temporal por clase).
**Pasos:** cada prueba ejecuta las solicitudes HTTP que se ven en su método (login, listado, alta, edición, borrado, exportación, etc.), con el cliente de pruebas y la protección CSRF activa.
**Resultado esperado:** las afirmaciones (`assert`) del método: códigos HTTP, mensajes, datos persistidos y ausencia de información sensible.
**Responsable:** por completar por el integrante que ejecute/valide el caso en el repositorio del equipo.

Última ejecución completa: **66 de 66 aprobadas** (12-10-2026 19:33). Reproducir con `python tests/run_tests.py` (deja evidencia en `evidencias/resultados_automaticos.md`).

| ID | Módulo | Req. | Caso | Estado | Evidencia | Fecha |
|---|---|---|---|---|---|---|
| CP-ATN-01 | Ingreso de atención | 3 | Registro correcto con folio responsable y delegacion | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_01_registro_correcto_con_folio_responsable_y_delegacion | 12-10-2026 |
| CP-ATN-02 | Ingreso de atención | 3 | Campos obligatorios | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_02_campos_obligatorios | 12-10-2026 |
| CP-ATN-03 | Ingreso de atención | 3 | Dependencia tipo subatencion | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_03_dependencia_tipo_subatencion | 12-10-2026 |
| CP-ATN-04 | Ingreso de atención | 3 | Solo opciones activas | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_04_solo_opciones_activas | 12-10-2026 |
| CP-ATN-05 | Ingreso de atención | 3 | Prevencion de doble envio | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_05_prevencion_de_doble_envio | 12-10-2026 |
| CP-ATN-06 | Ingreso de atención | 3 | No se puede forzar delegacion ni responsable | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_06_no_se_puede_forzar_delegacion_ni_responsable | 12-10-2026 |
| CP-ATN-07 | Ingreso de atención | 3 | Usa la delegacion activa tras cambiar contexto | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_07_usa_la_delegacion_activa_tras_cambiar_contexto | 12-10-2026 |
| CP-ATN-08 | Ingreso de atención | 3 | Solicitante busqueda y alta rapida | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_08_solicitante_busqueda_y_alta_rapida | 12-10-2026 |
| CP-ATN-09 | Ingreso de atención | 3 | Solicitante inexistente | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_09_solicitante_inexistente | 12-10-2026 |
| CP-ATN-10 | Ingreso de atención | 3 | Cancelar no crea registros | Aprobada (automática) | tests/test_sgr.py::test_CP_ATN_10_cancelar_no_crea_registros | 12-10-2026 |
| CP-AUT-01 | Acceso | 1 | Login correcto por usuario | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_01_login_correcto_por_usuario | 12-10-2026 |
| CP-AUT-02 | Acceso | 1 | Login correcto por correo | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_02_login_correcto_por_correo | 12-10-2026 |
| CP-AUT-03 | Acceso | 1 | Clave incorrecta mensaje generico | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_03_clave_incorrecta_mensaje_generico | 12-10-2026 |
| CP-AUT-04 | Acceso | 1 | Campos vacios | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_04_campos_vacios | 12-10-2026 |
| CP-AUT-05 | Acceso | 1 | Cuenta inactiva | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_05_cuenta_inactiva | 12-10-2026 |
| CP-AUT-06 | Acceso | 1 | Bloqueo por intentos | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_06_bloqueo_por_intentos | 12-10-2026 |
| CP-AUT-07 | Acceso | 1 | Cierre de sesion y rutas protegidas | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_07_cierre_de_sesion_y_rutas_protegidas | 12-10-2026 |
| CP-AUT-08 | Acceso | 1 | Rutas protegidas sin sesion | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_08_rutas_protegidas_sin_sesion | 12-10-2026 |
| CP-AUT-09 | Acceso | 1 | Csrf obligatorio | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_09_csrf_obligatorio | 12-10-2026 |
| CP-AUT-10 | Acceso | 1 | Next no permite redireccion externa | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_10_next_no_permite_redireccion_externa | 12-10-2026 |
| CP-AUT-11 | Acceso | 1 | Cuenta desactivada pierde acceso de inmediato | Aprobada (automática) | tests/test_sgr.py::test_CP_AUT_11_cuenta_desactivada_pierde_acceso_de_inmediato | 12-10-2026 |
| CP-CRUD-01 | Mantenedores (6 CRUD) | 2 | Ciclo completo de los seis mantenedores | Aprobada (automática) | tests/test_sgr.py::test_CP_CRUD_01_ciclo_completo_de_los_seis_mantenedores | 12-10-2026 |
| CP-CRUD-02 | Mantenedores (6 CRUD) | 2 | Campos requeridos y formatos | Aprobada (automática) | tests/test_sgr.py::test_CP_CRUD_02_campos_requeridos_y_formatos | 12-10-2026 |
| CP-CRUD-03 | Mantenedores (6 CRUD) | 2 | Longitudes maximas | Aprobada (automática) | tests/test_sgr.py::test_CP_CRUD_03_longitudes_maximas | 12-10-2026 |
| CP-CRUD-04 | Mantenedores (6 CRUD) | 2 | Duplicados | Aprobada (automática) | tests/test_sgr.py::test_CP_CRUD_04_duplicados | 12-10-2026 |
| CP-CRUD-05 | Mantenedores (6 CRUD) | 2 | Restricciones por relaciones | Aprobada (automática) | tests/test_sgr.py::test_CP_CRUD_05_restricciones_por_relaciones | 12-10-2026 |
| CP-DEL-01 | Delegaciones | 2, 5 | No se desactiva la delegacion activa | Aprobada (automática) | tests/test_sgr.py::test_CP_DEL_01_no_se_desactiva_la_delegacion_activa | 12-10-2026 |
| CP-LST-01 | Listados y Excel | 4 | Busqueda parcial sin mayusculas ni tildes | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_01_busqueda_parcial_sin_mayusculas_ni_tildes | 12-10-2026 |
| CP-LST-02 | Listados y Excel | 4 | Busqueda en varios campos y terminos | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_02_busqueda_en_varios_campos_y_terminos | 12-10-2026 |
| CP-LST-03 | Listados y Excel | 4 | Caracteres especiales en busqueda | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_03_caracteres_especiales_en_busqueda | 12-10-2026 |
| CP-LST-04 | Listados y Excel | 4 | Paginacion y total | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_04_paginacion_y_total | 12-10-2026 |
| CP-LST-05 | Listados y Excel | 4 | Filtros combinados se mantienen al paginar | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_05_filtros_combinados_se_mantienen_al_paginar | 12-10-2026 |
| CP-LST-06 | Listados y Excel | 4 | Exportacion coincide con la tabla y con todas las paginas | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_06_exportacion_coincide_con_la_tabla_y_con_todas_las_paginas | 12-10-2026 |
| CP-LST-07 | Listados y Excel | 4 | Exportacion no incluye campos sensibles | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_07_exportacion_no_incluye_campos_sensibles | 12-10-2026 |
| CP-LST-08 | Listados y Excel | 4 | Exportacion neutraliza formulas | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_08_exportacion_neutraliza_formulas | 12-10-2026 |
| CP-LST-09 | Listados y Excel | 4 | Exportar requiere permiso | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_09_exportar_requiere_permiso | 12-10-2026 |
| CP-LST-10 | Listados y Excel | 4 | Ordenamiento | Aprobada (automática) | tests/test_sgr.py::test_CP_LST_10_ordenamiento | 12-10-2026 |
| CP-PER-01 | Perfil y delegación | 5 | Menu diferenciado por rol | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_01_menu_diferenciado_por_rol | 12-10-2026 |
| CP-PER-02 | Perfil y delegación | 5 | Acceso directo a modulos no autorizados | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_02_acceso_directo_a_modulos_no_autorizados | 12-10-2026 |
| CP-PER-03 | Perfil y delegación | 5 | Distintivo muestra delegacion usuario y rol | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_03_distintivo_muestra_delegacion_usuario_y_rol | 12-10-2026 |
| CP-PER-04 | Perfil y delegación | 5 | Selector solo con delegaciones autorizadas | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_04_selector_solo_con_delegaciones_autorizadas | 12-10-2026 |
| CP-PER-05 | Perfil y delegación | 5 | Cambio de contexto actualiza listados | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_05_cambio_de_contexto_actualiza_listados | 12-10-2026 |
| CP-PER-06 | Perfil y delegación | 5 | No se puede cambiar a delegacion ajena | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_06_no_se_puede_cambiar_a_delegacion_ajena | 12-10-2026 |
| CP-PER-07 | Perfil y delegación | 5 | Acceso a registros de otra delegacion por id | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_07_acceso_a_registros_de_otra_delegacion_por_id | 12-10-2026 |
| CP-PER-08 | Perfil y delegación | 5 | Superadmin ve todas las delegaciones | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_08_superadmin_ve_todas_las_delegaciones | 12-10-2026 |
| CP-PER-09 | Perfil y delegación | 5 | Opciones de formularios respetan el alcance | Aprobada (automática) | tests/test_sgr.py::test_CP_PER_09_opciones_de_formularios_respetan_el_alcance | 12-10-2026 |
| CP-REC-01 | Recuperación de contraseña | 1 | Respuesta no revela si el correo existe | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_01_respuesta_no_revela_si_el_correo_existe | 12-10-2026 |
| CP-REC-02 | Recuperación de contraseña | 1 | Correo invalido o vacio | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_02_correo_invalido_o_vacio | 12-10-2026 |
| CP-REC-03 | Recuperación de contraseña | 1 | Flujo completo y clave anterior rechazada | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_03_flujo_completo_y_clave_anterior_rechazada | 12-10-2026 |
| CP-REC-04 | Recuperación de contraseña | 1 | Codigo incorrecto vencido y reutilizado | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_04_codigo_incorrecto_vencido_y_reutilizado | 12-10-2026 |
| CP-REC-05 | Recuperación de contraseña | 1 | Reenvio respeta espera de 45 segundos | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_05_reenvio_respeta_espera_de_45_segundos | 12-10-2026 |
| CP-REC-06 | Recuperación de contraseña | 1 | Intentos fallidos agotan el codigo | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_06_intentos_fallidos_agotan_el_codigo | 12-10-2026 |
| CP-REC-07 | Recuperación de contraseña | 1 | Nueva clave sin verificacion es rechazada | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_07_nueva_clave_sin_verificacion_es_rechazada | 12-10-2026 |
| CP-REC-08 | Recuperación de contraseña | 1 | Requisitos y confirmacion de clave | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_08_requisitos_y_confirmacion_de_clave | 12-10-2026 |
| CP-REC-09 | Recuperación de contraseña | 1 | Cambio de clave cierra sesiones abiertas | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_09_cambio_de_clave_cierra_sesiones_abiertas | 12-10-2026 |
| CP-REC-10 | Recuperación de contraseña | 1 | Codigo no se guarda en claro | Aprobada (automática) | tests/test_sgr.py::test_CP_REC_10_codigo_no_se_guarda_en_claro | 12-10-2026 |
| CP-ROL-01 | Roles | 2, 5 | Escalamiento de privilegios | Aprobada (automática) | tests/test_sgr.py::test_CP_ROL_01_escalamiento_de_privilegios | 12-10-2026 |
| CP-ROL-02 | Roles | 2, 5 | Un coordinador no asigna rol superior ni delegaciones ajenas | Aprobada (automática) | tests/test_sgr.py::test_CP_ROL_02_un_coordinador_no_asigna_rol_superior_ni_delegaciones_ajenas | 12-10-2026 |
| CP-SEG-01 | Seguridad | 1, 5 | Ninguna respuesta filtra hashes | Aprobada (automática) | tests/test_sgr.py::test_CP_SEG_01_ninguna_respuesta_filtra_hashes | 12-10-2026 |
| CP-SEG-02 | Seguridad | 1, 5 | Cabeceras y cookie | Aprobada (automática) | tests/test_sgr.py::test_CP_SEG_02_cabeceras_y_cookie | 12-10-2026 |
| CP-SEG-03 | Seguridad | 1, 5 | Salida html escapada | Aprobada (automática) | tests/test_sgr.py::test_CP_SEG_03_salida_html_escapada | 12-10-2026 |
| CP-SEG-04 | Seguridad | 1, 5 | Inyeccion sql en login | Aprobada (automática) | tests/test_sgr.py::test_CP_SEG_04_inyeccion_sql_en_login | 12-10-2026 |
| CP-SEG-05 | Seguridad | 1, 5 | Salud | Aprobada (automática) | tests/test_sgr.py::test_CP_SEG_05_salud | 12-10-2026 |
| CP-TIP-01 | Tipo y Sub Atención | 2 | Tipo y subatencion integridad | Aprobada (automática) | tests/test_sgr.py::test_CP_TIP_01_tipo_y_subatencion_integridad | 12-10-2026 |
| CP-TIP-02 | Tipo y Sub Atención | 2 | Subatencion duplicada en mismo tipo | Aprobada (automática) | tests/test_sgr.py::test_CP_TIP_02_subatencion_duplicada_en_mismo_tipo | 12-10-2026 |
| CP-USR-01 | Usuarios | 2 | Reglas de usuarios | Aprobada (automática) | tests/test_sgr.py::test_CP_USR_01_reglas_de_usuarios | 12-10-2026 |

## 3. Pruebas de interfaz y de entorno (manuales o semiautomáticas)

Se ejecutó una **prueba de humo de interfaz** con Chromium (`python tests/ui_smoke.py`, capturas en `evidencias/capturas/`): inicio de sesión, recuperación (pasos 1 y 2), recorrido de los seis mantenedores, alta y baja de un ítem desde la pantalla, búsqueda sin coincidencias, matriz de permisos de roles, ingreso de atención con lista dependiente y actualización del listado, cambio de delegación y vista móvil. Resultado: **sin errores de JavaScript**. **Limitación:** el entorno de prueba no tenía Internet, por lo que SweetAlert2 (CDN) no cargó y esa ejecución usó el respaldo de diálogos nativos. Los casos MAN-01 a MAN-04 siguen **pendientes** hasta repetirlos con SweetAlert2 real.

| ID | Req. | Módulo | Precondiciones | Pasos | Resultado esperado | Estado | Evidencia | Responsable | Fecha |
|---|---|---|---|---|---|---|---|---|---|
| MAN-01 | 6 | SweetAlert2 · éxito real | Sesión superadmin, Internet | Crear un ítem válido | Alerta de éxito solo tras respuesta 201; el listado muestra el registro | Pendiente (flujo verificado sin SweetAlert2) | | | |
| MAN-02 | 6 | SweetAlert2 · validación fallida | Ídem | Guardar formulario vacío | Alerta de advertencia + errores junto a cada campo; no se llama a la API | Pendiente | | | |
| MAN-03 | 6 | SweetAlert2 · error de servidor | Ídem | Detener el servicio y pulsar Guardar | Alerta de error «No se pudo conectar…»; no aparece éxito | Pendiente | | | |
| MAN-04 | 6 | SweetAlert2 · eliminar y cancelar | Ídem | Eliminar → Cancelar; Eliminar → Confirmar | Cancelar no modifica nada; confirmar elimina y avisa | Pendiente | | | |
| MAN-05 | 1 | Código de 6 dígitos | Código en `/dev/bandeja` | Pegar el código completo; moverse con flechas y retroceso | Se reparte en las casillas; navegación por teclado | Pendiente | | | |
| MAN-06 | 1 | Mostrar/ocultar clave | — | Pulsar «Mostrar» en login y paso 3 | Alterna visibilidad; `aria-pressed` cambia | Pendiente | | | |
| MAN-07 | 2, 5 | Adaptabilidad | — | Abrir en 390 px, 768 px y 1280 px | Menú colapsable, tabla en tarjetas, sin desborde | Parcial (captura 390 px) | evidencias/capturas/16_movil_funcionario.png | | |
| MAN-08 | 5 | Cambios sin guardar | Coordinador con 2 delegaciones | Abrir formulario, escribir, cambiar delegación | Pregunta de confirmación; «Quedarme aquí» conserva el contexto | Pendiente | | | |
| MAN-09 | 5 | Teclado y foco | — | Recorrer una pantalla con Tab/Shift+Tab/Esc | Foco visible, orden lógico, Esc cierra el diálogo | Pendiente | | | |
| MAN-10 | 5 | Normas gráficas oficiales | Manual oficial descargado | Reemplazar logotipo y ajustar tipografía/colores; comparar | Coincide con el manual | **Pendiente** (el logotipo es un marcador de posición) | | | |
| MAN-11 | 7 | Despliegue AWS | Instancia lista | Abrir `https://…/salud` | `estado: ok` y la versión/commit entregados | Pendiente | | | |
| MAN-12 | 4 | Excel en Excel/LibreOffice | — | Exportar con un filtro y abrir el archivo | Mismas filas que la tabla (todas las páginas); hoja «Filtro aplicado» | Pendiente (la coherencia está probada automáticamente: CP-LST-06) | | | |
| MAN-13 | 5 | Demostración de roles | 4 cuentas demo | Ingresar con cada rol y recorrer el menú | Cada rol ve solo lo autorizado (ver `docs/MATRIZ_PERMISOS.md`) | Pendiente de demostración (probado automáticamente: CP-PER-01/02) | | | |
| MAN-14 | 1 | Correo real | SMTP/SES configurado | Solicitar un código a un correo real | Llega el mensaje con código de 6 dígitos | Pendiente (hoy el correo es **simulado**) | | | |

## 4. Prueba de estrés

Herramienta: `tests/stress/stress_test.py` (solo librería estándar). Mezcla de operaciones reales (listado, búsqueda, registro de atención, exportación) con concurrencia creciente (1, 5, 10, 25, 50…) hasta degradar o llegar al límite seguro.

- **Umbrales de aceptación propuestos (definir y firmar antes de ejecutar):** p95 ≤ 800 ms y errores ≤ 1 % por etapa; recuperación con 1 usuario tras la carga sin errores.
- **Estado:** el script fue **validado localmente** (servidor de desarrollo, entorno de pruebas) solo para comprobar que funciona; esos números **no sirven como resultado de la entrega**. La ejecución contra AWS está **pendiente**; usar la plantilla `docs/RESULTADOS_ESTRES.md`.

## 5. Registro de defectos

| ID | Hallazgo | Estado |
|---|---|---|
| DEF-01 | El icono de la lupa se superponía a la etiqueta del buscador (detectado en la captura de interfaz). | Corregido en `sgr.css`. |
| DEF-02 | La prueba de estrés inicial mostró 9 % de errores con 1 usuario: eran 403 correctos, porque el rol Funcionario no puede exportar. | No es un defecto del sistema; el script usa ahora el rol Delegado. |

> Los defectos DEF-01 y DEF-02 son los hallados durante el desarrollo. Agreguen aquí los que aparezcan en sus pruebas manuales y en AWS.
