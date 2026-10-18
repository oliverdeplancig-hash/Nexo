# Nexo

**Repositório institucional + assistente virtual com IA.**
Conexão entre documentos, setores e pessoas: servidores encontram normas e procedimentos, entendem o que
fazer e descobrem qual setor pode ajudar — sempre dentro do que o seu perfil pode acessar.

## O que o Nexo faz

- **Repositório documental** com classificação de acesso (geral, setor, restrito), autorizações por
  usuário/setor/perfil com validade, versões, coleções, favoritos e download protegido.
- **Assistente** em tempo real (WebSocket) que responde em três camadas:
  1. **Motor determinístico** — regras aprovadas respondem sem IA, sempre do mesmo jeito, com fontes;
  2. **Busca híbrida** (texto + significado + nome) apenas nos documentos autorizados;
  3. **IA local (Ollama)** com citações `[n]` verificadas — e, se a IA cair, os trechos relevantes.
- **Avaliação das respostas e lacunas do assistente**: o servidor marca se a resposta ajudou; quem gere as regras
  vê perguntas sem resposta ou mal avaliadas e cria regras a partir delas.
- **Vigência e revisão** de documentos: revogados saem do assistente e da busca, mas continuam para consulta;
  lembretes de revisão periódica para quem mantém cada documento.
- **Painel do acervo** para a gestão: vigência, revisões por setor e documentos mais consultados.
- **Coleções** pessoais e institucionais: criar, editar, excluir e organizar documentos, sem mexer em permissões.
- **Ajuda** adaptada ao perfil, com botão "?" que abre o tópico da tela atual.
- **Diretório de setores**: "Qual setor pode me ajudar?".
- **Importação** de PDF, DOCX, TXT, MD e HTML com extração, metadados sugeridos e indexação.
- **Login institucional** pela conta Microsoft (`@pm.ba.gov.br`), com contas locais para demonstração —
  configuração em [docs/security/login-microsoft.md](docs/security/login-microsoft.md).
- **Administração** de usuários, perfis e matriz de permissões por documento.
- **Auditoria** somente-inserção encadeada por hash, com verificação de integridade.
- **Cópia de segurança** diária do banco e dos arquivos num pacote cifrado e verificável, com restauração
  segura — [docs/architecture/copia-de-seguranca.md](docs/architecture/copia-de-seguranca.md).
- **PWA responsiva**: desktop, tablet e smartphone com o mesmo app.

## Estrutura

```
Nexo/
├── CLAUDE.md                          contexto e hierarquia de regras
├── 01 — Engineering Operating System/ como trabalhamos
├── 02 — Architecture Rules/           regras arquiteturais (RA-NN)
├── 03 — Project Rules/                regras de negócio (RN-NNN), linguagem, glossário
├── docs/                              arquitetura, ADRs, requisitos, segurança, banco, API, testes
├── backend/                           Django 5 + DRF + Channels + pgvector
│   ├── nexo/                          configurações, ASGI, rotas
│   ├── apps/                          acesso · auditoria · busca · comum · contas · conversas ·
│   │                                  documentos · ia · ingestao · motor · notificacoes · organizacao
│   └── demo/documentos/               documentos FICTÍCIOS para demonstração
├── frontend/                          React 18 + TypeScript + MUI + PWA (Vite)
├── deploy/                            systemd e nginx para o servidor Linux
├── scripts/                           iniciar-local.ps1 · instalar-servidor.sh
└── docker-compose.dev.yml             PostgreSQL+pgvector e Ollama (apenas desenvolvimento)
```

## Início rápido (local)

```bash
# 1. Banco e IA (com Docker Desktop; sem Docker veja docs/architecture/implantacao.md)
docker compose -f docker-compose.dev.yml up -d
docker exec -it $(docker ps -qf name=ollama) ollama pull qwen2.5:7b-instruct
docker exec -it $(docker ps -qf name=ollama) ollama pull bge-m3

# 2. Backend
cd backend
python -m venv .venv && . .venv/bin/activate        # Windows: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
cp .env.example .env
python manage.py migrate
python manage.py inicializar_nexo
python manage.py carregar_demo                      # usuários admin.demo / servidor.demo / ti.demo
daphne -b 127.0.0.1 -p 8000 nexo.asgi:application

# 3. Frontend
cd ../frontend && npm install && npm run dev        # http://localhost:5173
```

Sem Ollama instalado, use `NEXO_IA_PROVEDOR=falso` no `.env` para demonstrar o fluxo completo com um
provedor determinístico.

Senha dos usuários de demonstração: `Nexo@demo2026` (somente com `NEXO_DEBUG=true`).

## Qualidade

```bash
cd backend && python -m pytest && ruff check .     # 117 testes
cd frontend && npm run build                       # checagem de tipos + build PWA
cd frontend && npm run e2e                         # ponta a ponta + acessibilidade (Playwright)
```

## Documentação

- Arquitetura: [docs/architecture/visao-geral.md](docs/architecture/visao-geral.md)
- Motor determinístico e IA: [docs/architecture/ia-e-motor.md](docs/architecture/ia-e-motor.md)
- Implantação: [docs/architecture/implantacao.md](docs/architecture/implantacao.md)
- Decisões: [docs/adr/](docs/adr/README.md)
- Segurança: [docs/security/](docs/security/modelo-de-autorizacao.md)
- API e WebSocket: [docs/api/README.md](docs/api/README.md)
