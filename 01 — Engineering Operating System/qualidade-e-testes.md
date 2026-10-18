# Qualidade e testes

## Backend
- `ruff` com `ruff.toml` (linha de 120 colunas). `ruff format` antes de entregar.
- Testes com `pytest` + `pytest-django` contra PostgreSQL real (pgvector e busca textual não são simuláveis).
- Provedor de IA **falso e determinístico** nos testes (`nexo.settings_teste`); nenhum teste chama rede.
- Toda regra de autorização tem teste de **propriedade**: o filtro de banco deve coincidir com a decisão
  individual (`test_filtro_de_banco_equivale_a_decisao_individual`).

## Frontend
- TypeScript estrito; `npm run build` executa a checagem de tipos.
- Componentes de tela em `src/paginas`, componentes reutilizáveis em `src/componentes`.
- Tokens visuais somente via `src/tema.ts` (design system "Institutional Intelligence").

## Revisão
- Toda mudança em `apps/acesso`, `apps/conversas/orquestrador.py`, `apps/motor` ou `apps/auditoria`
  exige revisão com foco em segurança.
