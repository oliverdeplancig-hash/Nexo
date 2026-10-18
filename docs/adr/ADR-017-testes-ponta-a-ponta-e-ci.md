# ADR-017 — Testes de ponta a ponta, acessibilidade automática e integração contínua

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O backend tem testes automatizados contra PostgreSQL real, mas o frontend só tinha checagem de tipos; os
fluxos de tela eram verificados manualmente. Nada rodava sozinho a cada envio: um teste fora do padrão de
formatação chegou ao repositório porque a verificação foi feita depois do commit. A definição de pronto exige
funcionamento em smartphone e navegação acessível, sem verificação automática.

## Decisão
- **Testes de ponta a ponta** com Playwright (`frontend/e2e/`, `npm run e2e`) em navegador real contra o
  backend de verdade, com banco próprio (`*_e2e`, zerado a cada execução por `scripts/e2e-servidor.sh`),
  dados de demonstração e IA falsa. Cobrem: menu por perfil, recusa de rota administrativa, login inválido,
  assistente com resposta aprovada e fonte, avaliação negativa chegando às lacunas sem identificar o autor,
  coleções (criar, organizar, excluir), revogação e restabelecimento, Ajuda por perfil e versão para
  smartphone (sem rolagem horizontal).
- **Acessibilidade automática** com axe-core nas telas principais de cada perfil: violações **sérias ou
  críticas** das WCAG 2.1 A/AA reprovam o teste.
- **Integração contínua** no GitHub Actions (`.github/workflows/ci.yml`) a cada envio para `main` e em pull
  requests: backend (`ruff` + `pytest` com pgvector), frontend (tipos + build) e, se ambos passarem, ponta a
  ponta. Relatório do Playwright fica disponível por 7 dias quando há falha.
- **Somente dados fictícios** no CI: dados de demonstração e IA falsa. Nenhum documento institucional, `.env`
  ou segredo vai ao GitHub (compatível com a ADR-004).
- O limite de tentativas de login passa a ser configurável (`NEXO_LIMITE_LOGIN`, padrão **10/min**, com teste
  de regressão); só o ambiente de ponta a ponta o afrouxa.
- Novas dependências de desenvolvimento, com versão fixa: `@playwright/test` e `@axe-core/playwright`.

## Alternativas consideradas
- **Testes de componente (Vitest + Testing Library):** mais rápidos, mas não pegam integração com a API,
  permissões e WebSocket — onde estão os riscos do Nexo. Podem complementar depois.
- **Cypress:** equivalente, mas o Playwright já era usado nas verificações manuais e cobre smartphone.
- **CI no servidor da instituição (GitLab, Jenkins):** preferível se a instituição hospedar o código
  internamente; o workflow é simples de portar.

## Consequências
- Todo envio passa a ser verificado automaticamente; quebras de tela e de acessibilidade aparecem antes do uso.
- A suíte de ponta a ponta leva alguns minutos; roda depois dos testes rápidos.
- Acessibilidade de nível "moderado" ainda não reprova; pode ser endurecida depois.
- Backlog: rodar a suíte também no Windows local, cobrir importação com OCR e cópia de segurança via tela.
