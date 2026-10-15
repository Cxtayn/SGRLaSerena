# Despliegue en AWS (EC2 + nginx + gunicorn)

Arquitectura mínima: **1 instancia EC2** (Ubuntu 24.04, t3.small o similar) con nginx → gunicorn → Flask, base SQLite en el volumen EBS. Opcional: Elastic IP, dominio en Route 53 y HTTPS con Let's Encrypt (o ALB + ACM).

## Servicios y componentes
| Componente | Uso |
|---|---|
| EC2 | Ejecuta la aplicación (servicio `sgr` de systemd) |
| EBS | Disco con `/var/lib/sgr/sgr.sqlite3` (hacer snapshots) |
| Security Group | Entrada 80/443 pública; 22 solo desde la IP del equipo |
| Elastic IP / Route 53 | Dirección fija y dominio |
| SES (opcional) | Correo real para códigos de recuperación (SMTP) |
| CloudWatch (opcional) | CPU/memoria durante la prueba de estrés |

## Pasos
1. Crear la instancia y el Security Group. Conectarse por SSH.
2. Subir el código al repositorio remoto Git y crear la etiqueta de la entrega: `git tag v2.0.0-entrega2 && git push --tags`.
3. En la instancia: `sudo bash deploy/instalar_ec2.sh <URL_REPO> v2.0.0-entrega2` (instala paquetes, crea usuario `sgr`, venv, base con datos demo, servicio y nginx).
4. Verificar: `curl http://localhost/salud` → debe mostrar `estado: ok` y la versión/commit.
5. HTTPS: `sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx -d TU-DOMINIO`; luego en `/etc/sgr/sgr.env` poner `SESSION_COOKIE_SECURE=1` y `sudo systemctl restart sgr`.
6. Correo real (opcional): en `/etc/sgr/sgr.env` poner `MAIL_MODE=smtp`, `SMTP_HOST`, `SMTP_PORT=587`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` (identidad verificada en SES) y `DEV_OUTBOX=0`.
7. Acceso de evaluación: acordar con el docente qué cuentas usar (las demo o una nueva con `python manage.py crear-superadmin`).

## Actualizar a una nueva versión
`sudo bash /opt/sgr/deploy/actualizar_ec2.sh <commit-o-etiqueta>` (hace checkout, instala dependencias, actualiza `GIT_COMMIT` y reinicia). La versión desplegada se ve en el pie de página y en `/salud`.

## Secretos
`SECRET_KEY` se genera en el servidor y vive solo en `/etc/sgr/sgr.env` (permisos 640). No subir `.env`, claves SMTP ni capturas que las muestren.

## Pendiente de verificar por el equipo
Este documento y los scripts se escribieron sin acceso a una cuenta AWS: **no se ejecutaron en AWS**. Prueben la instalación en una instancia limpia y corrijan lo que corresponda.
