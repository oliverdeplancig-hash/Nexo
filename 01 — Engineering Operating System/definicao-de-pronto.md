# Definição de pronto

Uma mudança está pronta quando:

- [ ] Atende ao requisito descrito e aos critérios de aceite.
- [ ] Respeita o motor de permissões: nenhum acesso documental decidido fora de `apps/acesso/servico.py`.
- [ ] Tem testes automatizados cobrindo o caminho principal e os casos de negação de acesso.
- [ ] `pytest`, `ruff check .`, `npm run build` e `npm run e2e` passam sem erros (a integração contínua
      confere tudo a cada envio — ADR-017).
- [ ] Eventos relevantes geram registro de auditoria (sem conteúdo de documentos ou conversas).
- [ ] Textos de interface em português do Brasil, datas DD/MM/AAAA e horas em 24 h.
- [ ] Funciona em smartphone (≤ 767 px) e desktop, com navegação por teclado e foco visível.
- [ ] Documentação e ADRs atualizadas quando aplicável.
