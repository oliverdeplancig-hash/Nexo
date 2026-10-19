# Capacidade e dimensionamento (ADR-020)

## Onde está o limite
Cada pergunta passa primeiro pelo **motor determinístico** (ADR-003). Se houver regra, a resposta sai em
milissegundos. Sem regra, a busca encontra os trechos autorizados e a **IA local** escreve a resposta. A
plataforma (telas, busca, permissões, banco) atende 100 pessoas com folga num computador comum; o que limita
é **quantas respostas por minuto a IA consegue gerar**.

Conta para dimensionar (lei de Little):

```
perguntas para a IA por segundo  = pessoas × perguntas por pessoa por minuto ÷ 60 × fração sem regra
gerações simultâneas necessárias = perguntas para a IA por segundo × segundos para gerar uma resposta
tokens por segundo necessários   = perguntas para a IA por segundo × tokens por resposta (~250)
```

| Cenário | Perguntas para a IA | Tokens/s necessários | Ordem de grandeza do hardware de IA |
|---|---|---|---|
| 100 pessoas, 1 pergunta/min, 1/3 com regra | ~1,1/s | ~280 | 1 GPU dedicada de bom porte com modelo de 7–8 B; em CPU, a fila e as respostas com trechos serão frequentes |
| 100 pessoas, 1 pergunta a cada 5 min | ~0,2/s | ~55 | GPU de entrada; CPU potente ainda gera fila nos picos |
| 10 mil pessoas, 1 pergunta/min, 1/3 com regra | ~110/s | ~28 000 | várias dezenas de GPUs de datacenter com servidor de inferência com lotes (ex.: vLLM), atrás de balanceador |
| 10 mil pessoas, 1 pergunta a cada 10 min, 2/3 com regra | ~5,6/s | ~1 400 | poucas GPUs de datacenter |

Os números de hardware são estimativas para orientar a compra; **meça no equipamento real** com o teste
abaixo. A forma mais barata de ganhar capacidade é **criar regras do motor para as perguntas mais
frequentes** (painel de lacunas, ADR-012): cada pergunta respondida por regra não usa a IA.

## Ajustes (backend/.env)
| Variável | Padrão | O que faz |
|---|---|---|
| `NEXO_IA_CONCORRENCIA` | 2 | Gerações ao mesmo tempo por processo web; o supervisor do Windows passa o mesmo valor ao Ollama (`OLLAMA_NUM_PARALLEL`). Aumente só se a memória da GPU/CPU comportar. |
| `NEXO_IA_FILA_MAXIMA` | 50 | Perguntas que podem esperar a vez. Acima disso, resposta na hora com trechos. |
| `NEXO_IA_ESPERA_MAXIMA` | 45 | Segundos de espera antes de responder com trechos. |
| `NEXO_DB_POOL_MAXIMO` | 0 (servidor: 40) | Conexões do banco por processo web. Some todos os processos e mantenha abaixo do `max_connections` do PostgreSQL (100). |
| `NEXO_REDIS_URL` | — | Obrigatório com mais de um processo web: tempo real e limites compartilhados. |

## Teste de carga
Rode num ambiente de homologação ou fora do expediente (gera conversas reais da conta usada):

```
cd backend
python manage.py teste_carga --url https://nexo-pc --usuario <conta de teste> --pessoas 100 --minutos 5 ^
    --sem-verificar-certificado
```

O relatório mostra perguntas atendidas por minuto, tempo até a resposta (mediana, 95% e pior), a origem das
respostas, quantas esperaram na fila da IA e quantas foram respondidas só com trechos.

**Como ler:** respostas do motor e telas devem ficar abaixo de 1 s. Se muitas respostas saem só com trechos,
falta capacidade de IA: crie regras para as perguntas frequentes, use um modelo menor ou um equipamento com
GPU, e só então aumente `NEXO_IA_CONCORRENCIA`.

## Nuvem (muitos usuários)
1. Vários processos web: `systemctl enable --now nexo-web@8001 nexo-web@8002 …`
   (`deploy/systemd/nexo-web@.service`) e as linhas correspondentes no `upstream nexo_web` do nginx.
2. Redis (`NEXO_REDIS_URL`) para tempo real, limites de requisição e de login.
3. PostgreSQL dimensionado, com PgBouncer ou `NEXO_DB_POOL_MAXIMO` ajustado ao número de processos.
4. Servidores de IA hospedados pela instituição (ADR-004) com GPU, atrás de balanceador
   (`NEXO_OLLAMA_URL` apontando para ele).
5. Processador da fila de documentos (`nexo-ingestao`) separado dos processos web.
