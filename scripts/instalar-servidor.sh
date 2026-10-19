#!/usr/bin/env bash
# Instalação/atualização no servidor Linux (sem Docker). Execute como root.
set -euo pipefail
DESTINO=/opt/nexo
DADOS=/var/lib/nexo
id nexo >/dev/null 2>&1 || useradd --system --home "$DESTINO" --shell /usr/sbin/nologin nexo
mkdir -p "$DADOS/armazenamento" "$DADOS/copias"
chown -R nexo:nexo "$DADOS"
cd "$DESTINO/backend"
[ -d .venv ] || sudo -u nexo python3 -m venv .venv
sudo -u nexo .venv/bin/pip install -q -r requirements.txt
[ -f .env ] || { cp .env.example .env; echo "Edite $DESTINO/backend/.env antes de continuar."; exit 1; }
sudo -u nexo .venv/bin/python manage.py migrate --noinput
sudo -u nexo .venv/bin/python manage.py collectstatic --noinput
sudo -u nexo .venv/bin/python manage.py inicializar_nexo
cp "$DESTINO/deploy/systemd/"*.service "$DESTINO/deploy/systemd/"*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now nexo-web nexo-ingestao nexo-copia.timer
grep -q '^NEXO_ATRAS_DE_PROXY=true' .env || echo "ATENÇÃO: atrás do nginx, defina NEXO_ATRAS_DE_PROXY=true no .env (HTTPS e cookies seguros)."
grep -q '^NEXO_DB_POOL_MAXIMO=[1-9]' .env || echo "Recomendado: NEXO_DB_POOL_MAXIMO=40 no .env (muitas pessoas ao mesmo tempo, ADR-020)."
grep -q '^NEXO_BACKUP_SENHA=.' .env || echo "ATENÇÃO: defina NEXO_BACKUP_SENHA no .env (as cópias diárias falham sem ela)."
echo "Nexo instalado. Publique $DESTINO/frontend/dist no servidor web (ver deploy/nginx/nexo.conf)."
