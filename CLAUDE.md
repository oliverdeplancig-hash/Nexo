# CLAUDE.md — Nexo

## 1. Contexto do Projeto

- **Objetivo do sistema:** repositório institucional de documentos com assistente virtual que responde a
  servidores com base apenas em documentos autorizados, indica fontes e encaminha ao setor responsável.
- **Domínio:** gestão do conhecimento institucional em órgão público (normas, procedimentos, manuais,
  diretório de setores), com controle de acesso por setor, perfil e documento.
- **Stack tecnológica:** Python 3.11+, Django 5.1, Django REST Framework, Django Channels (WebSocket),
  PostgreSQL 15+ com pgvector e unaccent, Ollama (LLM e embeddings locais), React 18 + TypeScript +
  Material UI (PWA responsiva), Vite.
- **Restrições relevantes:**
  - Começa em um computador local e depois vai para o servidor da instituição (Linux, sem Docker,
    PostgreSQL 15). Docker é apenas conveniência de desenvolvimento.
  - Nenhum dado institucional sai da rede: IA somente local (Ollama) — ADR-004.
  - Toda resposta passa primeiro pelo motor determinístico (ADR-003).
  - O acesso a documentos é decidido exclusivamente por `apps/acesso/servico.py` (ADR-005).
  - Não inventar logotipos, nomes de órgãos, contatos ou fontes.

## 2. Hierarquia de Regras

As regras devem ser interpretadas na seguinte ordem:

1. Project Rules
2. Architecture Rules
3. Engineering Operating System
4. Conhecimento de referência

Em caso de conflito, uma regra mais específica prevalece sobre uma regra mais genérica,
desde que não viole restrições superiores do projeto. Regras de segurança nunca são afrouxadas.

## 3. Engineering Operating System

Consultar:
- `01 — Engineering Operating System/`

## 4. Architecture

Consultar:
- `02 — Architecture Rules/`

## 5. Project

Consultar:
- `03 — Project Rules/`

## 6. Documentation

A documentação oficial do projeto está em:
- `docs/architecture/`
- `docs/adr/`
- `docs/requirements/`
- `docs/security/`
- `docs/database/`
- `docs/api/`
- `docs/testing/`

## 7. ADR

Decisões arquiteturais relevantes devem ser registradas em:

`docs/adr/`

Antes de propor uma mudança arquitetural, verificar se existe
uma ADR relacionada ao assunto. Formato `ADR-NNN`, status inicial **Proposta**,
índice em `docs/adr/README.md`.

**ADR automática (regra do usuário):** toda funcionalidade nova ou mudança de comportamento que
envolva uma decisão ainda não registrada — modelo de dados, regra de acesso ou privacidade,
integração externa, dependência nova, formato de arquivo, operação (cópia, implantação), padrão de
interface — sai **com a sua ADR no mesmo commit**, sem esperar pedido. Se a mudança altera uma
decisão existente, criar nova ADR que a substitui (ADR aceita não se edita). Atualizar o índice e
citar a ADR no módulo principal e na documentação afetada. Correções de defeito e ajustes que não
mudam decisão não precisam de ADR.

## 8. Comandos frequentes

```bash
# backend
cd backend && python -m pytest            # testes (provedor de IA falso)
ruff check . && ruff format --check .     # qualidade
python manage.py processar_fila --continuo
# frontend
cd frontend && npm run dev                # http://localhost:5173 (proxy para :8000)
npm run build
```

## 9. Git

Não fazer commit nem push sem pedido explícito. Mensagens em português, no imperativo.
