# ADR-020 — Capacidade: 100 pessoas ao mesmo tempo na rede local e caminho para 10 mil na nuvem

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Requisito: cerca de **100 pessoas usando ao mesmo tempo** no computador da instituição (ADR-019) e, no
futuro, cerca de **10 mil na nuvem**, cada uma interagindo **a cada minuto**.

O teste de carga (`manage.py teste_carga`) mostrou três problemas no código anterior:
1. As etapas síncronas do assistente (banco, busca, permissões) de **todas as conversas abertas** no processo
   rodavam numa **única linha de execução**, em fila.
2. Cada pergunta **segurava uma conexão do banco enquanto esperava a IA**. Com a IA ocupada, as conexões
   acabavam e até as telas e as respostas do motor determinístico ficavam lentas ou falhavam.
3. A IA local é o recurso mais caro: num computador comum ela gera uma ou duas respostas por vez. Sem limite,
   todas as gerações disputavam o modelo ao mesmo tempo e ninguém recebia resposta em tempo razoável.

## Decisão
- **Uma linha de execução por pergunta** no WebSocket (`ThreadSensitiveContext` em
  `apps/conversas/consumers.py`), com a conexão devolvida ao terminar.
- **Conexão devolvida antes de esperar a IA** (`orquestrador._devolver_conexao`).
- **Conjunto de conexões** do psycopg (`NEXO_DB_POOL_MAXIMO`, 40 no servidor): quem passar do limite espera
  uma conexão livre em vez de falhar; o PostgreSQL não passa de 100 conexões.
- **Fila da IA** (`apps/ia/fila.py`): no máximo `NEXO_IA_CONCORRENCIA` gerações por processo (o Ollama recebe
  `OLLAMA_NUM_PARALLEL` igual). As demais esperam, vendo "Aguardando a vez: N perguntas à frente". Com mais de
  `NEXO_IA_FILA_MAXIMA` esperando ou passados `NEXO_IA_ESPERA_MAXIMA` segundos (45), a pessoa recebe **na
  hora** os trechos mais relevantes dos documentos autorizados (resposta extrativa, com fontes), com aviso.
  Isso não vira lacuna do assistente (ADR-012), pois não é falta de conhecimento.
- O **motor determinístico** (ADR-003), a busca, as telas e "sem fontes" **não passam pela fila**: continuam
  instantâneos mesmo com a IA lotada. Quanto mais perguntas frequentes viram regra, menos carga na IA.
- **Teste de carga** reproduzível: `python manage.py teste_carga --url ... --pessoas 100 --minutos 5`.
- **Nuvem (vários processos)**: `NEXO_REDIS_URL` liga o Redis para mensagens em tempo real **e** para os
  limites de requisição e de login; `deploy/systemd/nexo-web@.service` sobe processos extras e o nginx
  distribui (`upstream nexo_web`). O nginx passa o IP real (`X-Forwarded-For` sobrescrito) para a auditoria
  e para o limite de login por endereço — sem isso, todas as pessoas apareceriam com o IP do proxy e
  dividiriam o mesmo limite.

## Medição (contêiner de desenvolvimento, IA simulada)
| Cenário (100 pessoas, 1 pergunta/min cada) | Resultado |
|---|---|
| IA instantânea | 200/200 respondidas; 95% em até 0,1 s; telas em até 0,0 s |
| IA a 10 palavras/s, 4 gerações por vez, código anterior | mediana 60 s, 26 conexões perdidas, telas até 5 s |
| Mesmo cenário com esta decisão | motor e telas ≤ 0,1 s; IA com fila; 53 de 264 respondidas na hora com trechos |

A plataforma atende 100 pessoas com folga; o limite real é **quantas respostas por minuto a IA consegue
gerar** no hardware disponível. Dimensionamento em [capacidade.md](../architecture/capacidade.md).

## Alternativas consideradas
- **Fila no banco com processo separado para a IA**: sobrevive a reinícios, mas acrescenta latência e
  complexidade para respostas que são transmitidas ao vivo; a fila em memória basta com prazo curto.
- **Rejeitar perguntas acima da capacidade**: pior para quem pergunta do que receber os trechos com fontes.
- **Cache de respostas por pergunta**: perigoso com permissões por documento (a mesma pergunta tem fontes
  diferentes para pessoas diferentes); fica para estudo com chave pelo conjunto de documentos visíveis.
- **IA em serviço externo para absorver picos**: proibido pela ADR-004.

## Consequências
- Em horário de pico, parte das perguntas abertas recebe trechos em vez de texto gerado. O painel de lacunas
  não mistura esses casos.
- O tamanho da fila é por processo; com vários processos, a capacidade total é a soma, limitada pelo
  servidor de IA.
- Para 10 mil pessoas é obrigatório: vários processos web, Redis, PgBouncer ou conjunto de conexões ajustado,
  servidores de IA com GPU dimensionados pela tabela de capacidade e regras do motor para as perguntas mais
  frequentes.
