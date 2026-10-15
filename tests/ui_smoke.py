"""Prueba de humo de interfaz con Playwright (Chromium). Genera capturas en evidencias/capturas.
Uso: python tests/ui_smoke.py http://localhost:5000
Nota: sin Internet el CDN de SweetAlert2 no carga y se usa el respaldo con diálogos nativos."""
import re, sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:5000"
CAP = "evidencias/capturas/"
errores, dialogos = [], []

def login(page, u):
    page.goto(BASE + "/login"); page.fill("#usuario", u); page.fill("#password", "Demo#2026Sgr!")
    page.click("#btn-ingresar"); page.wait_for_url(re.compile(r"/$"))

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.on("console", lambda m: errores.append(m.text) if m.type == "error" and "ERR_" not in m.text and "Failed to load resource" not in m.text else None)
    page.on("pageerror", lambda e: errores.append(str(e)))
    page.on("dialog", lambda d: (dialogos.append(d.message[:90]), d.accept()))
    page.goto(BASE + "/login"); page.screenshot(path=CAP + "01_login.png")
    page.click("text=¿Olvidaste tu contraseña?"); page.screenshot(path=CAP + "02_recuperar_paso1.png")
    page.fill("#correo", "delegado2@example.test"); page.click("#btn-enviar"); page.wait_for_url("**/recuperar/validar")
    page.screenshot(path=CAP + "03_recuperar_paso2.png")
    login_ok = None
    login(page, "superadmin"); page.screenshot(path=CAP + "04_inicio_superadmin.png")
    for ruta, nombre in [("/delegaciones", "05_delegaciones"), ("/roles", "06_roles"), ("/usuarios", "07_usuarios"),
                         ("/items", "08_items"), ("/tipos-atencion", "09_tipos"), ("/sub-atenciones", "10_subatenciones")]:
        page.goto(BASE + ruta); page.wait_for_selector("table.tabla"); page.screenshot(path=CAP + nombre + ".png")
    # crear un ítem desde la UI
    page.goto(BASE + "/items"); page.wait_for_selector("table.tabla")
    page.click("#btn-nuevo"); page.wait_for_selector("#f-codigo")
    page.fill("#f-codigo", "it95"); page.fill("#f-nombre", "Ítem creado por UI"); page.screenshot(path=CAP + "11_form_item.png")
    page.click("#btn-guardar"); page.wait_for_timeout(800)
    page.fill("#buscador", "creado por ui"); page.wait_for_timeout(700)
    assert "Ítem creado por UI" in page.inner_text("#zona-tabla"), "no aparece el registro creado"
    # búsqueda sin coincidencias
    page.fill("#buscador", "zzzzzz"); page.wait_for_timeout(700)
    assert "Sin coincidencias" in page.inner_text("#zona-tabla")
    page.screenshot(path=CAP + "12_sin_coincidencias.png")
    page.fill("#buscador", "creado por ui"); page.wait_for_timeout(700)
    page.click('[data-acc="eliminar"]'); page.wait_for_timeout(900)
    page.fill("#buscador", "creado por ui"); page.wait_for_timeout(700)
    assert "Sin coincidencias" in page.inner_text("#zona-tabla"), "no se eliminó"
    # roles: matriz
    page.goto(BASE + "/roles"); page.wait_for_selector("table.tabla"); page.click("#btn-nuevo"); page.wait_for_selector(".matriz")
    page.screenshot(path=CAP + "13_form_rol_matriz.png")
    # atención
    page.goto(BASE + "/atenciones"); page.wait_for_selector("#tipo_id option:nth-child(2)", state="attached")
    page.select_option("#tipo_id", index=1); page.wait_for_timeout(200)
    assert page.locator("#subtipo_id option").count() > 1
    page.fill("#vecino-buscar", "cam"); page.wait_for_selector("#vecino-lista li[data-i]"); page.click("#vecino-lista li[data-i]")
    page.select_option("#subtipo_id", index=1); page.fill("#descripcion", "Solicitud creada desde la prueba de interfaz.")
    page.screenshot(path=CAP + "14_ingreso_atencion.png")
    n0 = page.inner_text("#paginador")
    page.click("#btn-guardar-atencion"); page.wait_for_timeout(1200)
    assert page.inner_text("#paginador") != n0, "la lista no se actualizó"
    # cambio de tipo limpia subatención
    page.select_option("#tipo_id", index=1); page.select_option("#subtipo_id", index=1)
    page.select_option("#tipo_id", index=2); assert page.input_value("#subtipo_id") == ""
    # cambio de contexto (superadmin)
    page.select_option("#selector-delegacion", index=1); page.wait_for_load_state(); page.wait_for_timeout(600)
    assert "DEL02" in page.inner_text("#distintivo-delegacion")
    page.screenshot(path=CAP + "15_contexto_cambiado.png")
    # móvil
    m = b.new_context(viewport={"width": 390, "height": 800}).new_page()
    m.goto(BASE + "/login"); m.fill("#usuario", "funcionario"); m.fill("#password", "Demo#2026Sgr!"); m.click("#btn-ingresar")
    m.wait_for_url(re.compile(r"/$")); m.goto(BASE + "/atenciones"); m.wait_for_selector("table.tabla")
    m.screenshot(path=CAP + "16_movil_funcionario.png")
    ctx.close(); b.close()
print("Diálogos nativos usados (respaldo sin CDN):", len(dialogos))
print("Errores de consola/JS:", errores or "ninguno")
