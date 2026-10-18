# ADR-016 — Painel do acervo e aviso de regra com fonte revogada

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Com vigência e revisão (ADR-015), a gestão documental passou a ter pendências (revisões atrasadas, documentos
sem data de revisão, revogações), mas não tinha uma visão consolidada por setor nem sabia quais documentos são
mais usados. Além disso, a revogação de um documento citado por uma regra do motor só aparecia como marca na
tela de regras: quem mantém a regra podia não ver.

## Decisão
- **Painel do acervo** (`/painel-acervo`, endpoint `painel/acervo/`) para quem tem `importar_documentos`,
  `gerir_regras` ou `ver_auditoria`, com: totais (vigentes, revogados, revisões atrasadas e próximas, vigentes
  sem revisão programada), tabela por setor responsável, lista das revisões atrasadas e os 10 documentos mais
  abertos no período (7, 30 ou 90 dias).
- **Todos os números saem de `documentos_visiveis(usuario)`** (ADR-005): o painel não conta nem lista
  documentos fora do acesso de quem o abre — duas pessoas podem ver números diferentes.
- "Mais consultados" vem dos eventos `DOCUMENTO_ABERTO` da auditoria, **apenas como contagem por
  documento**: o painel nunca mostra quem abriu, nem setor de quem abriu.
- **Aviso de fonte revogada:** ao revogar um documento, quem criou cada regra **publicada** que o cita recebe
  notificação (`regra_fonte_revogada`); se o criador não gere mais regras, todos com `gerir_regras` recebem.
  Rascunhos não geram aviso. Completa a ADR-015, que mantém a regra respondendo com alerta até a revisão.
- Lógica em `apps/documentos/painel.py`; cálculo sob demanda (sem tabelas de agregação).

## Alternativas consideradas
- **Painel com todo o acervo para administradores:** revelaria contagens e títulos de documentos restritos,
  contrariando a ADR-005.
- **Ranking de consultas por pessoa ou setor:** ajudaria a medir adoção, mas expõe hábitos de leitura de
  servidores; fora do escopo e dependeria de decisão institucional sobre privacidade.
- **Agregações pré-calculadas (tabelas de estatística):** desnecessárias no volume atual; revisitar se o
  painel ficar lento.
- **Desligar a regra ao revogar a fonte:** descartado na ADR-015; o aviso leva a decisão a quem mantém a regra.

## Consequências
- A gestão documental passa a ter uma fila clara de trabalho (revisões e revogações) e um sinal de uso do
  acervo para priorizar revisões e novas respostas aprovadas.
- O painel consulta a auditoria; com muitos eventos, a consulta de "mais consultados" pode precisar de índice
  por `(tipo, ocorrido_em)` — `ocorrido_em` já é indexado.
- Backlog: exportar o painel em planilha, série histórica de revisões e alertas por e-mail.
