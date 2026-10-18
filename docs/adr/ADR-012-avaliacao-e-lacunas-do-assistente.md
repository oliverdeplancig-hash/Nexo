# ADR-012 — Avaliação das respostas e lacunas do assistente

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O motor determinístico (ADR-003) só melhora se alguém souber quais perguntas ficam sem resposta ou recebem
respostas ruins. Sem esse retorno, as regras são escritas por suposição. Ao mesmo tempo, as perguntas dos
servidores podem conter assuntos pessoais, e as respostas podem trazer trechos de documentos restritos que a
equipe que mantém as regras não pode ler (ADR-005).

## Decisão
- O **autor** da pergunta avalia cada resposta do assistente: útil / não útil, com motivo (incorreta,
  incompleta, não respondeu, desatualizada, setor errado, outro) e comentário opcional
  (`AvaliacaoResposta`, uma por mensagem).
- **Lacuna** = resposta sem fontes suficientes, resposta só com trechos (IA indisponível) ou resposta avaliada
  como não útil. Quem tem `gerir_regras` vê as lacunas e indicadores (respostas, % por regra aprovada,
  % úteis, pendentes) em Motor de respostas → Lacunas do assistente.
- **Minimização de dados** na lista de lacunas: mostra a pergunta, a origem, a avaliação, a regra usada ou a
  mais próxima e as fontes que o gestor pode consultar; **não mostra** autor (nome ou setor) nem o texto da
  resposta.
- A lacuna é **tratada** (`TratamentoLacuna`) criando ou ajustando uma regra a partir dela, ou marcando sem
  ação; tratar e reabrir geram evento `LACUNA_TRATADA` na auditoria.
- Apagar a conversa apaga pergunta, avaliação e lacuna (o servidor controla o próprio histórico).

## Alternativas consideradas
- **Mostrar a conversa completa ao gestor:** mais contexto, mas expõe o servidor e documentos restritos.
- **Anonimizar com IA antes de mostrar:** custo e risco de falha silenciosa; a pergunta isolada basta para
  criar regras.
- **Analisar só o rastro técnico (sem avaliação humana):** não detecta resposta errada com fonte válida.

## Consequências
- Ciclo de melhoria contínua do motor com base em uso real, sem exportar dados para fora (ADR-004).
- Perguntas ficam visíveis para a gestão do motor sem identificação; o texto da ajuda orienta o servidor a não
  escrever dados pessoais no comentário.
- Backlog: agrupar perguntas parecidas (mesma lacuna) e alertar quando uma regra recebe muitas avaliações
  negativas.
