# ADR-001 — Monólito modular em Django com frontend React separado

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O Nexo começa em um único computador e depois vai para o servidor da instituição (Linux, sem Docker,
PostgreSQL 15). Há um único desenvolvedor. A especificação pede Python, Django REST Framework,
PostgreSQL/pgvector, React e Material UI.

## Decisão
Backend como **monólito modular** Django (`backend/apps/<domínio>`) servindo API REST e WebSocket por ASGI
(daphne), e frontend React + TypeScript + MUI (`frontend/`) como SPA/PWA, servido como estático.

## Alternativas consideradas
- **Microsserviços (API, IA, ingestão separados):** rejeitado — custo operacional alto para um desenvolvedor e servidor sem orquestrador.
- **Django com templates (sem SPA):** rejeitado — chat em streaming, painel contextual e PWA ficam mais complexos.
- **FastAPI:** rejeitado — perderia admin, ORM, migrações e autenticação prontos do Django.

## Consequências
- Um processo ASGI + um worker de ingestão bastam em produção.
- Fronteiras entre apps precisam ser mantidas por regra (RA-01) e revisão.
- Backlog: avaliar separação do worker de embeddings se o volume crescer.
