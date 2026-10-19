## O que muda
<!-- Uma ou duas frases. Mensagem de commit em português, no imperativo. -->

## Por quê
<!-- Pedido, defeito ou lacuna que motivou a mudança. -->

## Verificação
- [ ] `ruff check . && ruff format --check .` e `python -m pytest` no backend
- [ ] `npm run build` e, se mexeu em telas, `npm run e2e` no frontend
- [ ] Testes novos cobrem o comportamento novo ou o defeito corrigido

## Decisões e segurança
- [ ] Decisão nova ou alterada tem **ADR no mesmo PR** (`docs/adr/`, índice atualizado) — ou não se aplica
- [ ] Acesso a documentos continua decidido só por `apps/acesso/servico.py` (ADR-005)
- [ ] Nenhum dado institucional sai da rede; IA somente local (ADR-004)
- [ ] Nenhuma senha, chave, `.env`, cópia `.nexobak` ou planilha de usuários no PR
- [ ] Documentação afetada atualizada (`docs/`, Ajuda, `CHANGELOG.md`)
