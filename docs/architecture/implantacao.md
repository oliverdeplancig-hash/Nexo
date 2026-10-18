# Implantação

## 1. Computador local (Windows) — desenvolvimento e uso individual

Pré-requisitos: Python 3.11+, Node 20+, PostgreSQL 15+ com pgvector, Ollama.

> Atalho: com Docker Desktop, `docker compose -f docker-compose.dev.yml up -d` sobe PostgreSQL+pgvector
> e Ollama. Sem Docker, instale o PostgreSQL e a extensão pgvector (ver `docs/database/README.md`).

```powershell
# Banco
psql -U postgres -c "CREATE USER nexo WITH PASSWORD 'nexo';"
psql -U postgres -c "CREATE DATABASE nexo OWNER nexo;"
psql -U postgres -d nexo -c "CREATE EXTENSION IF NOT EXISTS vector; CREATE EXTENSION IF NOT EXISTS unaccent;"

# OCR (documentos digitalizados) — ver ADR-009
scripts\instalar-ocr.cmd

# Modelos de IA
ollama pull qwen2.5:7b-instruct
ollama pull bge-m3

# Backend
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env     # ajuste NEXO_SECRET_KEY e o banco
python manage.py migrate
python manage.py inicializar_nexo
python manage.py carregar_demo          # opcional: dados fictícios de demonstração
python manage.py createsuperuser        # para o /django-admin/ em modo DEBUG
daphne -b 127.0.0.1 -p 8000 nexo.asgi:application

# Frontend (outro terminal)
cd frontend
npm install
npm run dev     # http://localhost:5173
```

Ou use `scripts/iniciar-local.ps1`.

## 2. Servidor da instituição (Linux, sem Docker, PostgreSQL 15)

1. Pacotes: `python3.11+ python3-venv postgresql-15-pgvector postgresql-client-15 tesseract-ocr tesseract-ocr-por` (ou compilar o pgvector), Node apenas para
   gerar o build (pode ser feito em outra máquina).
2. Usuário de sistema `nexo`; código em `/opt/nexo`; arquivos em `/var/lib/nexo/armazenamento` (fora da web).
3. `.env` de produção: `NEXO_DEBUG=false`, `NEXO_SECRET_KEY` forte, `NEXO_ALLOWED_HOSTS`,
   `NEXO_CSRF_TRUSTED_ORIGINS=https://nexo.<dominio>`, `NEXO_COOKIE_SEGURO=true`,
   `NEXO_PROCESSAR_IMEDIATAMENTE=false`, `NEXO_REDIS_URL` se houver Redis.
4. `python manage.py migrate && python manage.py collectstatic && python manage.py inicializar_nexo`.
5. Frontend: `npm ci && npm run build` → publicar `frontend/dist`.
6. Serviços systemd em `deploy/systemd/`: `nexo-web.service` (daphne), `nexo-ingestao.service` (worker) e
   `nexo-copia.timer` (cópia de segurança diária).
7. Proxy reverso: `deploy/nginx/nexo.conf` (HTTPS, estáticos, `/api` e `/ws` para o daphne).
   Se a TI não permitir Nginx, o daphne pode servir diretamente atrás do proxy corporativo
   existente, mantendo HTTPS na borda; nesse caso sirva `frontend/dist` por um servidor estático
   aprovado pela TI.
8. Ollama no próprio servidor ou em máquina com GPU da rede interna (`NEXO_OLLAMA_URL`).

## Cópia de segurança
Cópia diária do banco e dos arquivos num único pacote cifrado, com verificação e restauração por comando —
procedimentos em [copia-de-seguranca.md](copia-de-seguranca.md) (ADR-011).
- Servidor: `nexo-copia.timer` (02:30), pasta `/var/lib/nexo/copias`, `NEXO_BACKUP_SENHA` obrigatória.
- Windows: `scripts\agendar-copia-windows.cmd`.
