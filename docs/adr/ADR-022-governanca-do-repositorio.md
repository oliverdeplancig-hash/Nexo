# ADR-022 — Governança do repositório: versões, contribuição e verificações automáticas

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O Nexo já tinha README, documentação por área, ADRs, testes de ponta a ponta e CI (ADR-017). Comparado a
repositórios grandes, faltavam: registro de mudanças e versões, guia de contribuição, política de
segurança, modelos de issue e de pull request, verificações antes do commit, atualização acompanhada de
dependências e medida de cobertura dos testes. Isso pesa quando a TI da instituição e outras pessoas
passarem a manter o sistema, e quando ele for para a nuvem (ADR-019).

## Decisão
- **Versões SemVer** e **CHANGELOG.md** no formato Keep a Changelog; versão inicial `0.1.0`. Ao publicar,
  "Não lançado" vira a nova versão e o commit recebe a tag `vX.Y.Z`.
- **CONTRIBUTING.md** com as restrições do projeto, fluxo de ramo/PR, ADR automática, testes e commits.
- **SECURITY.md**: vulnerabilidades por canais internos da instituição, nunca em issue pública.
- **Modelos** de issue (defeito, funcionalidade; issue em branco desativada) e de PR com a lista de
  verificação de decisões, permissões, ADR-004 e arquivos sensíveis.
- **pre-commit** (`.pre-commit-config.yaml`): YAML válido, conflitos, arquivos grandes, chaves privadas,
  ruff e bloqueio de arquivos de senha, credenciais, `.env`, `.nexobak`, certificados e planilhas de
  usuários. Complementa o `.gitignore`.
- **Dependabot**: PRs semanais agrupados para pip e npm e mensais para as ações do GitHub; cada um passa pela
  CI antes de entrar. Nenhum dado institucional vai ao GitHub (só manifestos de dependências).
- **Cobertura** medida na CI com `pytest-cov`, com resumo na página da execução. Mínimo de 75%
  (`backend/.coveragerc`); era 79% ao adotar, sem contar os próprios testes nem as migrações. O mínimo
  sobe à medida que entram testes. Em 19/10/2026 subiu para 82% (cobertura de 85,7%).

## Alternativas consideradas e o que não se aplica
- **Dockerfile para produção**: contraria a restrição de servidor sem Docker; Docker continua só para
  desenvolvimento.
- **CODE_OF_CONDUCT**: típico de projeto aberto com comunidade externa; a conduta aqui segue as normas da
  instituição.
- **LICENSE**: depende de decisão da instituição sobre a titularidade e eventual abertura do código; não
  se escolhe licença sem essa decisão.
- **Especificação OpenAPI gerada** (ex.: drf-spectacular): útil para integrações da TI; fica como próximo
  passo com ADR própria, pois acrescenta dependência e precisa decidir quem pode ver o esquema.
- **Monorepo com ferramentas de orquestração**: o projeto tem só backend e frontend; não compensa.

## Consequências
- Mudanças rastreáveis por versão; revisão de PR com lista de verificação de segurança.
- Commits com arquivo sensível falham localmente quando o pre-commit está instalado.
- Dependabot vai abrir PRs que precisam ser revisados e aceitos por alguém.
