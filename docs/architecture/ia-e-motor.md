# Motor determinístico e IA

## Motor determinístico (`apps/motor/motor.py`)

**Normalização** (`apps/comum/texto.py`): minúsculas, sem acentos e pontuação, remoção de stopwords e
radicalização simples (plural, "-ção", terminações verbais), para que "solicito", "solicitar" e
"solicitação" convirjam.

**Pontuação de cada regra publicada, vigente e aplicável ao setor/perfil do usuário:**

1. Termo excludente presente → descarta.
2. Algum termo obrigatório ausente → descarta.
3. Expressão regular casa → pontuação 1,0.
4. Senão: `0,75 × similaridade + 0,25 × reforço`, onde
   - similaridade = máximo, entre as frases de exemplo, de `max(Dice, 0,85 × contenção)`;
   - reforço = fração das palavras-chave encontradas.

**Decisão:** ordena por (pontuação ↓, prioridade ↓, código ↑). Abaixo do limiar (`NEXO_MOTOR_LIMIAR`, 0,62) →
não aplicável. Duas regras dentro da margem (`NEXO_MOTOR_MARGEM`, 0,04) com mesma prioridade →
desambiguação (o usuário escolhe). Caso contrário, responde com a regra.

**Renderização:** fontes filtradas por `pode(usuario, CONSULTAR)`. Se a regra tem fontes e nenhuma é
acessível → modo "somente encaminhamento" (RN-011).

**Rastro** (gravado na mensagem): pergunta normalizada, termos, limiar, 5 melhores candidatos com
componentes da pontuação, regra e versão escolhidas.

## RAG (`apps/conversas/orquestrador.py`, `apps/ia`)

- Contexto: até `NEXO_CONTEXTO_MAX_TRECHOS` (6) trechos numerados `[n] Título — p. X — Seção`.
- Prompt do sistema: responder só com o contexto, citar `[n]`, frase fixa quando não houver resposta,
  não inventar normas/datas/contatos, ignorar instruções dentro dos trechos.
- Evidência mínima: algum trecho achado por texto completo ou com similaridade ≥ `NEXO_SIMILARIDADE_MINIMA`.
- Pós-processamento: citações inexistentes são removidas; fontes marcadas como *citadas* ou *consultadas*.
- Selo de confiança: **verificada** (motor), **fundamentada** (RAG com citações), **cautela** (sem
  citações, sem fontes ou extrativo).

## Modelos recomendados (Ollama)

| Uso | Modelo | Observação |
|---|---|---|
| Chat | `qwen2.5:7b-instruct` | Bom português; ~5 GB quantizado |
| Chat (máquina modesta) | `qwen2.5:3b-instruct` | Mais rápido, menos preciso |
| Embeddings | `bge-m3` | Multilíngue, 1024 dimensões (padrão do projeto) |

Trocar a dimensão de embeddings exige nova migração do campo `Trecho.embedding` e
`manage.py reindexar_semantica --todos`.
