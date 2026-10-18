# ADR-013 — Coleções pessoais e institucionais sem efeito sobre permissões

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Os servidores precisam reunir documentos por tema (pastas). O modelo `Colecao` existia, mas sem regras claras
de quem gerencia cada coleção: o próprio servidor não conseguia excluir a coleção pessoal, não havia como
incluir ou retirar documentos depois da importação, o filtro por coleção era ignorado e a tela do documento
expunha nomes de coleções pessoais de outras pessoas. Pastas costumam ser confundidas com permissão
("está na pasta do RH, então o RH vê") — no Nexo isso não pode acontecer (ADR-005).

## Decisão
- **Coleção nunca concede nem retira acesso.** Quem abre uma coleção vê apenas os documentos autorizados para
  si (`documentos_visiveis`); contagens também.
- Dois tipos, definidos na criação e imutáveis depois:
  - **pessoal** — visível, editável, excluível e organizável só por quem criou;
  - **institucional** — visível a todos; criar, editar, excluir e organizar exige `gerir_colecoes`.
- Só entram numa coleção documentos que quem organiza pode consultar; os demais são ignorados.
- Coleção pessoal de outra pessoa é invisível em todos os pontos: listagem, filtro `?colecao=`, tela do
  documento, edição de documento e importação (que só alteram as coleções que a pessoa organiza).
- Excluir a coleção remove o agrupamento (e subcoleções), nunca os documentos. Subcoleções não podem formar
  ciclo.
- Regras concentradas em `apps/documentos/colecoes.py`; endpoints `colecoes/{id}/documentos/`.
- Coleções não geram eventos de auditoria: não alteram acesso a conteúdo.

## Alternativas consideradas
- **Coleção com permissão própria (compartilhar a pasta):** prático, mas cria um segundo caminho de acesso
  fora do motor de permissões, difícil de auditar.
- **Coleções compartilhadas entre pessoas específicas:** útil para equipes; pode ser acrescentada depois
  como terceiro tipo, sem conceder acesso aos documentos.
- **Apenas coleções institucionais:** remove a organização pessoal, muito pedida no uso diário.

## Consequências
- A mesma coleção mostra conteúdos diferentes para pessoas diferentes; a tela explica isso ("documentos
  visíveis para você").
- Backlog: coleções de equipe/setor, ordenação manual dos documentos e navegação por subcoleções na
  interface.
