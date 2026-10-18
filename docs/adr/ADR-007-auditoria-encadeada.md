# ADR-007 — Auditoria somente-inserção encadeada por hash

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
É preciso registrar logins, aberturas, downloads, mudanças de permissão, consultas ao assistente e falhas
de autorização, com garantia de integridade e sem expor conteúdo.

## Decisão
Tabela `EventoAuditoria` somente-inserção: cada evento guarda o SHA-256 do anterior (cadeia), gravado sob
advisory lock. Gatilho no PostgreSQL bloqueia UPDATE/DELETE. Endpoint de verificação de integridade.
`detalhes` nunca contém conteúdo de documentos nem texto de perguntas.

## Alternativas consideradas
- **Somente logs de aplicação:** rejeitado — fáceis de alterar e difíceis de consultar.
- **django-auditlog:** rejeitado — registra diffs de modelos (pode conter conteúdo) e não garante imutabilidade.

## Consequências
- Expurgo por retenção requer procedimento formal do DBA.
- Gravação serializada; volume esperado é compatível.
