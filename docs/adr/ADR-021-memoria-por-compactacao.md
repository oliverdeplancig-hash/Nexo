# ADR-021 — Memória da conversa por compactação

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O assistente recebia literalmente só as últimas seis mensagens da conversa. Em conversas longas ele perdia o
assunto, e perguntas de continuação ("e o prazo?", "e para servidor cedido?") eram buscadas sozinhas, sem
encontrar o documento certo. Mandar a conversa inteira ao LLM deixaria cada resposta mais lenta e cara
(ADR-020) e poderia levar para o contexto trechos de documentos que a pessoa deixou de poder consultar.
Foi pedido aplicar o conceito de **compactação de conversas** para construir memória, **dentro da conversa**.

## Decisão
- **Janela recente literal + resumo compactado** (`apps/conversas/memoria.py`): as `NEXO_MEMORIA_JANELA`
  mensagens mais recentes (6) vão literais ao LLM; as anteriores são compactadas em `Conversa.memoria` e
  entram no contexto como "Resumo do início desta conversa", marcado como não-fonte e não citável.
- **Compactação determinística**, depois de cada resposta: guarda a pergunta (até 240 caracteres), a origem
  da resposta, os documentos citados (só os identificadores) e a regra usada. **Não copia o texto das
  respostas** e **não usa o LLM**, que fica livre para responder. No máximo `NEXO_MEMORIA_MAXIMO_ITENS` (12)
  itens; os mais antigos saem e são contados.
- **Permissões na hora do uso** (ADR-005): os títulos dos documentos do resumo são resolvidos pelo motor de
  permissões a cada pergunta; documento que a pessoa deixou de poder consultar some do resumo.
- **Perguntas de continuação** ("e …", "mas …", "quanto ao …", "nesse caso …", ou que retomam com "isso",
  "disso", "dele" etc.) são buscadas junto com a pergunta anterior da conversa. O rastro registra
  `continuacao`.
- **Escopo**: a memória é da conversa. Nada passa de uma conversa para outra nem de uma pessoa para outra.
  Apagar a conversa apaga a memória.
- Transparência: o Chat avisa quando as mensagens mais antigas foram resumidas; todas continuam visíveis.

## Alternativas consideradas
- **Resumo gerado pelo LLM**: resumo mais rico, porém consome a IA (o recurso escasso, ADR-020), pode
  inventar e pode copiar trechos sigilosos para o resumo.
- **Mandar a conversa inteira**: contexto crescente, respostas lentas, risco de permissão vencida.
- **Memória entre conversas (fatos da pessoa)**: não pedida agora; exigiria tela para ver e apagar e
  análise de privacidade própria.

## Consequências
- Conversas longas mantêm o assunto com custo de contexto constante.
- O resumo é simples (perguntas e documentos); nuances das respostas antigas se perdem de propósito.
- Campo novo `Conversa.memoria` (migração `conversas.0003`), incluído nas cópias de segurança (ADR-011).
