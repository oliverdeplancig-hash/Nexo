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

## 2. Computador da instituição como servidor de rede (Windows) — fase 1 (ADR-019)

Um computador Windows da instituição roda o Nexo e os demais servidores acessam pelo navegador ou pelo
aplicativo (PWA), pela rede interna.

**A TI precisa definir antes:**
- o computador: ligado o tempo todo, na rede cabeada, sem suspender; de preferência com 16 GB de memória ou
  mais e GPU se a IA local for usada por muitas pessoas ([capacidade.md](capacidade.md));
- **IP fixo** ou um **nome DNS** para ele (ex.: `nexo.<unidade>.local`);
- o certificado: distribuir o autoassinado gerado pelo instalador ou fornecer um da autoridade interna;
- o SMTP institucional para o envio de acesso (opcional, ADR-018);
- uma pasta de rede para guardar as cópias de segurança.

**Instalação** (como Administrador, na pasta do Nexo):
1. Instale Python 3.12 e, se for usar a IA, o Ollama (`scripts\ativar-ia-local.cmd` baixa os modelos).
2. Rode `scripts\instalar-servidor-windows.cmd`. Ele prepara tudo, pergunta o nome DNS, pede a senha do
   Windows para a tarefa automática e cria o primeiro administrador (a senha temporária aparece uma vez).
3. Distribua `backend\.certificados\nexo.cer` aos computadores da rede (política de grupo, "Autoridades de
   Certificação Raiz Confiáveis"), ou troque `nexo.key`/`nexo.crt` pelo certificado da TI.
4. Agende a cópia diária: `scripts\agendar-copia-windows.cmd` (ADR-011).
5. Usuários acessam `https://<nome ou IP>`; o administrador cadastra as pessoas em Administração.

**Operação:** a tarefa "Nexo - servidor" sobe na inicialização e religa o que cair (registro em
`scripts\servidor.log`). Parar: `scripts\parar-servidor-windows.cmd`. Atualizar: rodar o instalador de novo.
Restaurar cópia: `scripts\restaurar-windows.cmd` (para e religa o servidor sozinho).
Medir a capacidade: `python manage.py teste_carga` ([capacidade.md](capacidade.md)).

**Ensaio antes da instituição (modo de teste):** num computador parecido com o da instituição, numa
**cópia separada** da pasta do Nexo, rode `scripts\instalar-servidor-windows.cmd teste`. Diferenças: portas
8443 e 8080, servidor numa janela própria (sem início automático), energia do computador intocada,
documentos fictícios de demonstração e, sem Ollama, respostas por regra e por trechos. Outros "computadores
da rede" podem ser: o celular no mesmo Wi-Fi, outro PC, ou o **Windows Sandbox** (Windows Pro/Enterprise,
recurso opcional "Área Restrita do Windows"), que é uma máquina virtual descartável com rede própria.
Para medir com muitas pessoas: `python manage.py teste_carga` (ver [capacidade.md](capacidade.md)).
Para desfazer: `scripts\desinstalar-servidor-windows.cmd` (mantém os dados).

**Migração para a nuvem (fase 2):** instale o servidor Linux (seção 3) e restaure nele a última cópia
`.nexobak` do computador: banco e arquivos vão juntos, com verificação.

## 3. Servidor da instituição ou nuvem governamental (Linux, sem Docker, PostgreSQL 15)

1. Pacotes: `python3.11+ python3-venv postgresql-15-pgvector postgresql-client-15 tesseract-ocr tesseract-ocr-por` (ou compilar o pgvector), Node apenas para
   gerar o build (pode ser feito em outra máquina).
2. Usuário de sistema `nexo`; código em `/opt/nexo`; arquivos em `/var/lib/nexo/armazenamento` (fora da web).
3. `.env` de produção: `NEXO_DEBUG=false`, `NEXO_SECRET_KEY` forte, `NEXO_ALLOWED_HOSTS`,
   `NEXO_CSRF_TRUSTED_ORIGINS=https://nexo.<dominio>`, `NEXO_COOKIE_SEGURO=true`,
   `NEXO_PROCESSAR_IMEDIATAMENTE=false`, `NEXO_ATRAS_DE_PROXY=true`, `NEXO_DB_POOL_MAXIMO=40`,
   `NEXO_REDIS_URL` se houver Redis (obrigatório com mais de um processo web — ADR-020).
4. `python manage.py migrate && python manage.py collectstatic && python manage.py inicializar_nexo`.
5. Frontend: `npm ci && npm run build` → publicar `frontend/dist`.
6. Serviços systemd em `deploy/systemd/`: `nexo-web.service` (daphne), `nexo-ingestao.service` (worker) e
   `nexo-copia.timer` (cópia de segurança diária). Para muitas pessoas, processos extras com
   `nexo-web@.service` ([capacidade.md](capacidade.md)).
7. Proxy reverso: `deploy/nginx/nexo.conf` (HTTPS, estáticos, `/api` e `/ws` para o daphne).
   Se a TI não permitir Nginx, o daphne pode servir diretamente atrás do proxy corporativo
   existente, mantendo HTTPS na borda; nesse caso sirva `frontend/dist` por um servidor estático
   aprovado pela TI.
8. Ollama no próprio servidor ou em máquina com GPU da rede interna (`NEXO_OLLAMA_URL`).
9. E-mail pelo SMTP da instituição (`NEXO_EMAIL_HOST` e demais variáveis no `.env.example`) e
   `NEXO_URL_PUBLICA`, para o envio automático de usuário e senha temporária no cadastro (ADR-018).

## Cópia de segurança
Cópia diária do banco e dos arquivos num único pacote cifrado, com verificação e restauração por comando —
procedimentos em [copia-de-seguranca.md](copia-de-seguranca.md) (ADR-011).
- Servidor: `nexo-copia.timer` (02:30), pasta `/var/lib/nexo/copias`, `NEXO_BACKUP_SENHA` obrigatória.
- Windows: `scripts\agendar-copia-windows.cmd`.
