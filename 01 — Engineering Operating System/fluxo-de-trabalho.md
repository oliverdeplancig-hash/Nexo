# Fluxo de trabalho

1. **Entender** — registrar o requisito em `docs/requirements/` (ou atualizar um existente).
2. **Verificar decisões** — procurar ADR relacionada em `docs/adr/`. Mudança arquitetural sem ADR não entra.
3. **Planejar** — dividir em passos pequenos que deixem o sistema funcionando a cada passo.
4. **Implementar com teste** — o teste que prova a regra vem junto da mudança (ver `qualidade-e-testes.md`).
5. **Verificar** — `pytest`, `ruff check`, `npm run build`; conferir a tela em desktop e celular.
6. **Documentar** — atualizar docs afetadas (API, banco, segurança) no mesmo conjunto de mudanças.
7. **Entregar** — revisão, commit e implantação seguindo `docs/architecture/implantacao.md`.
