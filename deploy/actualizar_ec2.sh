#!/usr/bin/env bash
# Actualiza a un commit/etiqueta concreto:  sudo bash deploy/actualizar_ec2.sh v2.0.0-entrega2
set -euo pipefail
REF="${1:?Indica commit o etiqueta}"
cd /opt/sgr && git fetch --all --tags && git checkout "$REF"
.venv/bin/pip install -r requirements.txt
sed -i "s/^GIT_COMMIT=.*/GIT_COMMIT=$(git rev-parse --short HEAD)/" /etc/sgr/sgr.env
systemctl restart sgr && sleep 2 && curl -fs http://127.0.0.1:8000/salud
