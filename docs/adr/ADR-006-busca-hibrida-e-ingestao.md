# ADR-006 — Busca híbrida em PostgreSQL e ingestão por fila em banco

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
A busca deve combinar nome, conteúdo textual e significado. O servidor não usa Docker e talvez não tenha
Redis; deve haver poucas peças.

## Decisão
- Trechos com `tsvector` (configuração `nexo_pt` = português + unaccent) e `vector` (pgvector, índice HNSW).
- Fusão por **Reciprocal Rank Fusion** com desempate por id; destaque por `ts_headline` com marcadores de controle.
- Trechos nunca atravessam páginas (citação exata).
- Ingestão por **fila em banco**: documentos com status `recebido` são consumidos por `manage.py processar_fila`
  com `SELECT … FOR UPDATE SKIP LOCKED`; em instalação local pode processar na hora (`NEXO_PROCESSAR_IMEDIATAMENTE`).

## Alternativas consideradas
- **Elasticsearch/OpenSearch:** rejeitado — mais um serviço para operar.
- **Celery + Redis/RabbitMQ:** rejeitado como obrigatório — infraestrutura extra.
- **Banco vetorial dedicado (Qdrant, Chroma):** rejeitado — duplicaria permissões fora do PostgreSQL.

## Consequências
- PostgreSQL precisa das extensões `vector` e `unaccent` (ver docs/database).
- Documentos digitalizados sem OCR falham com mensagem clara; OCR fica no backlog.
