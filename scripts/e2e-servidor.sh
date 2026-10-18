#!/usr/bin/env bash
# Sobe o backend para os testes de ponta a ponta (ADR-017): banco próprio, zerado, com dados de demonstração.
# Usado pelo Playwright (frontend/playwright.config.ts) e pela integração contínua. NÃO use em produção.
set -euo pipefail
cd "$(dirname "$0")/../backend"
export NEXO_DEBUG=true NEXO_IA_PROVEDOR=falso NEXO_PROCESSAR_IMEDIATAMENTE=true NEXO_OCR_MOTOR=desligado
export NEXO_LIMITE_LOGIN=1000/min  # a suíte entra muitas vezes seguidas; produção mantém 10/min
export NEXO_DATABASE_URL="${E2E_DATABASE_URL:-postgres://nexo:nexo@localhost:5432/nexo_e2e}"
export NEXO_ARMAZENAMENTO_DIR="$PWD/.armazenamento-e2e"
export NEXO_BACKUP_DIR="$PWD/.copias-e2e"
export NEXO_CSRF_TRUSTED_ORIGINS="http://127.0.0.1:${E2E_PORTA_FRONTEND:-5174},http://localhost:${E2E_PORTA_FRONTEND:-5174}"
PY="${PYTHON:-python}"

# Cria o banco de testes se ainda não existir (o nome sempre termina em _e2e, por segurança).
"$PY" - <<'PYEOF'
import os, re, psycopg
url = os.environ["NEXO_DATABASE_URL"]
nome = url.rsplit("/", 1)[1].split("?")[0]
if not nome.endswith("_e2e") or not re.fullmatch(r"[a-z0-9_]+", nome):
    raise SystemExit(f"Banco de testes deve terminar em _e2e (recebido: {nome})")
with psycopg.connect(url.rsplit("/", 1)[0] + "/postgres", autocommit=True) as c:
    if not c.execute("SELECT 1 FROM pg_database WHERE datname = %s", [nome]).fetchone():
        c.execute(f'CREATE DATABASE "{nome}"')
PYEOF

"$PY" manage.py migrate --noinput -v0
"$PY" manage.py flush --noinput
rm -rf "$NEXO_ARMAZENAMENTO_DIR" "$NEXO_BACKUP_DIR"
"$PY" manage.py carregar_demo
exec "$PY" -m daphne -b 127.0.0.1 -p "${E2E_PORTA_BACKEND:-8001}" nexo.asgi:application
