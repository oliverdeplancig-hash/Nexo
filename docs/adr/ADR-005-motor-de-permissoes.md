# ADR-005 — Motor de permissões centralizado e filtro antes do ranqueamento

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O sistema mistura documentos gerais, de setor e restritos. Vazamentos típicos em RAG acontecem quando a
busca ranqueia tudo e filtra depois, ou quando contagens e facetas revelam a existência de conteúdo.

## Decisão
Um único módulo, `apps/acesso/servico.py`, decide acesso: `decidir()` (por documento, com motivos) e
`documentos_visiveis()` (filtro de banco equivalente). Busca, listagem, facetas, contexto da IA e histórico
partem sempre do conjunto filtrado. Documento inacessível responde 404. `is_superuser` não concede acesso.

## Alternativas consideradas
- **django-guardian (permissões por objeto):** rejeitado — não expressa classificação + setor + validade e gera muitas linhas.
- **Filtrar após a busca vetorial:** rejeitado — risco de vazamento e de resultados vazios.
- **Row Level Security no PostgreSQL:** promissor, mas aumenta acoplamento com o banco; candidato futuro como defesa em profundidade.

## Consequências
- Teste de propriedade garante equivalência entre `decidir` e `documentos_visiveis`.
- Toda nova consulta a documentos deve partir de `documentos_visiveis` (RA-02).
