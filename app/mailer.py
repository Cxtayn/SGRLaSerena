"""Envío de correo. MAIL_MODE=console es una SIMULACIÓN: guarda el mensaje en la
bandeja de desarrollo y no sale a Internet. MAIL_MODE=smtp envía de verdad."""
import logging
import smtplib
from email.message import EmailMessage

from flask import current_app

from .db import ahora_iso, get_db

log = logging.getLogger("sgr.mail")


def enviar_correo(destino, asunto, cuerpo):
    cfg = current_app.config
    if cfg["MAIL_MODE"] == "smtp" and cfg["SMTP_HOST"]:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = cfg["MAIL_FROM"], destino, asunto
        msg.set_content(cuerpo)
        try:
            with smtplib.SMTP(cfg["SMTP_HOST"], cfg["SMTP_PORT"], timeout=10) as smtp:
                smtp.starttls()
                if cfg["SMTP_USER"]:
                    smtp.login(cfg["SMTP_USER"], cfg["SMTP_PASSWORD"])
                smtp.send_message(msg)
            return True
        except Exception:  # no se informa al usuario: evita revelar si la cuenta existe
            log.exception("Fallo al enviar correo SMTP")
            return False
    db = get_db()
    db.execute("INSERT INTO bandeja_dev (destino, asunto, cuerpo, creado_en) VALUES (?,?,?,?)",
               (destino, asunto, cuerpo, ahora_iso()))
    db.commit()
    log.info("Correo simulado para %s (ver /dev/bandeja)", destino)
    return True
