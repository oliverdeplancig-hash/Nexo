# ADR-014 — Ajuda contextual por perfil, com conteúdo versionado no código

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O Nexo atende públicos com tarefas muito diferentes: servidor (consulta), gestão documental (importação,
regras, lacunas), administração (usuários, permissões, cópias) e auditoria. Um manual único confunde quem só
consulta e esconde o que importa para quem administra. A ajuda também não pode desatualizar em relação às
telas, e o Nexo roda sem acesso à internet (ADR-004), o que exclui ferramentas de ajuda hospedadas fora.

## Decisão
- Página **Ajuda** (`/ajuda`) dentro do próprio app, com tópicos agrupados (primeiros passos, encontrar
  informação, organizar, gestão documental, administração, auditoria).
- **Filtragem por função:** cada tópico declara a função que exige (`funcao`); a pessoa vê só os tópicos do
  seu perfil, mais um resumo do próprio perfil (setor, perfis e o que pode fazer).
- **Ajuda contextual:** cada tópico declara as telas a que se refere (`telas`); o botão "?" abre a Ajuda no
  tópico da tela atual.
- **Conteúdo como código** em `frontend/src/ajuda/conteudo.ts`: revisado junto com a tela que muda, no mesmo
  commit, e funciona offline (PWA, ADR-008). Busca na ajuda sem acentos, no próprio navegador.
- A filtragem por perfil é **orientação, não segurança**: a ajuda não contém dados; quem decide o acesso
  continua sendo o backend.

## Alternativas consideradas
- **Ajuda cadastrada no banco e editável por administradores:** permite ajustes sem nova versão, mas exige
  editor, permissões e revisão próprios; candidata para quando o conteúdo crescer.
- **Documentos de ajuda dentro do repositório (respondidos pelo assistente):** útil como complemento; o
  assistente já responde dúvidas de normas, mas instruções de tela precisam ser exatas e versionadas com a
  interface.
- **Manual em PDF:** desatualiza rápido e não se adapta ao perfil.

## Consequências
- Mudança de tela deve vir acompanhada da atualização do tópico correspondente (regra para revisão de código).
- Texto da ajuda não pode citar órgão, contatos ou nomes reais (CLAUDE.md): orienta a procurar "o
  administrador do Nexo no seu órgão".
- Backlog: tour guiado no primeiro acesso e tópicos editáveis pela instituição.
