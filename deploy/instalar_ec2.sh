#!/usr/bin/env bash
# Instalación inicial en una instancia EC2 Ubuntu 24.04. Ejecutar como root:  sudo bash instalar_ec2.sh <URL_REPO_GIT> [commit_o_etiqueta]
set -euo pipefail
REPO="${1:?Indica la URL del repositorio Git}"; REF="${2:-main}"
apt-get update && apt-get install -y python3-venv python3-pip nginx git
id sgr >/dev/null 2>&1 || useradd --system --create-home --shell /usr/sbin/nologin sgr
rm -rf /opt/sgr && git clone "$REPO" /opt/sgr && cd /opt/sgr && git checkout "$REF"
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
mkdir -p /etc/sgr /var/lib/sgr
if [ ! -f /etc/sgr/sgr.env ]; then
  cat > /etc/sgr/sgr.env <<ENV
APP_ENV=production
SECRET_KEY=$(python3 -c 'import secrets;print(secrets.token_hex(32))')
DATABASE_PATH=/var/lib/sgr/sgr.sqlite3
GIT_COMMIT=$(git rev-parse --short HEAD)
MAIL_MODE=console
DEV_OUTBOX=1
SESSION_COOKIE_SECURE=0
ENV
  chmod 640 /etc/sgr/sgr.env; chown root:sgr /etc/sgr/sgr.env
fi
set -a; . /etc/sgr/sgr.env; set +a
[ -f "$DATABASE_PATH" ] || .venv/bin/python manage.py init-db --demo --volumen 500
chown -R sgr:sgr /var/lib/sgr
cp deploy/gunicorn.service /etc/systemd/system/sgr.service
cp deploy/nginx.conf /etc/nginx/sites-available/sgr && ln -sf /etc/nginx/sites-available/sgr /etc/nginx/sites-enabled/sgr && rm -f /etc/nginx/sites-enabled/default
systemctl daemon-reload && systemctl enable --now sgr && nginx -t && systemctl restart nginx
echo "Listo. Verifica: curl http://localhost/salud"
