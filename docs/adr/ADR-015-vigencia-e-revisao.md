# ADR-015 — Vigência e revisão periódica de documentos

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Normas e procedimentos são revogados e substituídos. Até aqui o Nexo só conhecia versões de um mesmo
arquivo (`versao_anterior`) e o arquivamento: um documento revogado continuava na busca e alimentando o
assistente, que podia responder com uma regra que não vale mais — exatamente o motivo "desatualizada" das
avaliações (ADR-012). Também não havia lembrete para conferir documentos periodicamente.

## Decisão
- **Vigência** no documento: `vigente` (padrão) ou `revogado`, com data, motivo obrigatório e, opcionalmente,
  o documento que o **substitui** (outro documento, não uma versão).
- Documento revogado:
  - **continua no repositório** e pode ser aberto (consulta histórica), com faixa de aviso, motivo e link para o
    substituto — só se a pessoa puder consultá-lo (não revela documentos restritos, ADR-005);
  - **sai do assistente e da busca padrão** (`documentos_filtrados` exclui revogados); a busca pode incluí-los
    por opção; perguntar sobre um documento específico continua possível;
  - regras do motor que o citam como fonte **continuam respondendo**, mas a resposta ganha um aviso de que o
    fundamento foi revogado e o selo cai de "Resposta curada e aprovada" para "Confira com atenção"; na tela
    de regras elas aparecem com "Fonte revogada: revise". Não são desligadas automaticamente: a resposta é
    curada por pessoas e quem decide é a gestão do motor.
- **Revisão periódica**: `revisar_em` (próxima) e `revisado_em` (última). Quem mantém o documento é notificado
  `NEXO_REVISAO_ANTECEDENCIA_DIAS` (30) antes e, enquanto atrasada, a cada `NEXO_REVISAO_REPETIR_DIAS` (7).
  Destinatário: responsável → quem cadastrou → quem importa documentos no setor responsável. Os avisos são
  idempotentes e rodam no worker (`processar_fila --continuo`, a cada hora), no comando `avisar_revisoes` e na
  inicialização local do Windows.
- Nova versão conta como revisão; quem apontava a versão anterior como substituta passa a apontar a nova.
- Revogar, restabelecer e registrar revisão exigem permissão de **editar** o documento e geram
  `DOCUMENTO_ALTERADO` na auditoria (com a ação). Lógica em `apps/documentos/vigencia.py`.

## Alternativas consideradas
- **Arquivar em vez de revogar:** arquivado some do repositório e perde o valor histórico ("qual norma valia
  em março?"); arquivamento continua existindo para documentos que não devem mais ser consultados.
- **Desligar automaticamente as regras com fonte revogada:** evita resposta desatualizada, mas pode deixar o
  servidor sem resposta para um assunto ainda válido; preferimos sinalizar e notificar a gestão.
- **Vigência por datas (início/fim) com revogação automática:** útil para normas temporárias; pode ser
  acrescentada depois sobre os mesmos campos.

## Consequências
- O assistente deixa de citar normas revogadas sem intervenção técnica, assim que o documento é revogado.
- Quem mantém documentos recebe notificações periódicas; o repositório ganha a aba "Para revisar".
- Backlog: vigência futura (entra em vigor em), revogação parcial (dispositivos), relatório de revisões por
  setor e aviso automático à gestão do motor quando uma fonte de regra é revogada (atendido pela ADR-016).
