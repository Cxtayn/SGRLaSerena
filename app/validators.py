"""Validaciones reutilizables. Se ejecutan siempre en el servidor."""
import re

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}$")
CODIGO_RE = re.compile(r"^[A-Z0-9][A-Z0-9_\-]{1,19}$")
USUARIO_RE = re.compile(r"^[a-z0-9][a-z0-9._\-]{2,29}$")
TELEFONO_RE = re.compile(r"^\+?[0-9 ]{8,15}$")

PASSWORD_REQUISITOS = [
    ("len", "Al menos 10 caracteres", lambda p: len(p) >= 10),
    ("may", "Una letra mayúscula", lambda p: re.search(r"[A-ZÁÉÍÓÚÑ]", p) is not None),
    ("min", "Una letra minúscula", lambda p: re.search(r"[a-záéíóúñ]", p) is not None),
    ("num", "Un número", lambda p: re.search(r"[0-9]", p) is not None),
    ("sim", "Un símbolo (por ejemplo ! # $ %)", lambda p: re.search(r"[^A-Za-z0-9ÁÉÍÓÚÑáéíóúñ\s]", p) is not None),
]


def validar_password(p, *, contexto=()):
    """Devuelve mensaje de error o None."""
    if not isinstance(p, str) or not p:
        return "Ingresa la contraseña."
    if len(p) > 128:
        return "La contraseña no puede superar 128 caracteres."
    faltan = [txt for _, txt, fn in PASSWORD_REQUISITOS if not fn(p)]
    if faltan:
        return "La contraseña no cumple: " + "; ".join(t.lower() for t in faltan) + "."
    bajo = p.casefold()
    for c in contexto:
        if c and len(c) >= 4 and c.casefold() in bajo:
            return "La contraseña no debe contener tu usuario o correo."
    return None


def limpiar_texto(valor):
    if valor is None:
        return ""
    return re.sub(r"\s+", " ", str(valor)).strip()


def normalizar_rut(rut):
    rut = re.sub(r"[.\s]", "", str(rut or "")).upper()
    if "-" not in rut and len(rut) > 1:
        rut = rut[:-1] + "-" + rut[-1]
    return rut


def rut_valido(rut):
    rut = normalizar_rut(rut)
    m = re.fullmatch(r"(\d{7,8})-([\dK])", rut)
    if not m:
        return False
    cuerpo, dv = m.groups()
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    return dv == esperado


def enmascarar_correo(correo):
    correo = str(correo or "")
    if "@" not in correo:
        return "***"
    local, dominio = correo.split("@", 1)
    return f"{local[:1] or '*'}***@{dominio}"
