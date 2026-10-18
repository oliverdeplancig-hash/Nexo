# ADR-004 — IA local com Ollama

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Os documentos e perguntas são institucionais e podem ser sensíveis. O servidor da instituição tem acesso
à internet, mas os dados não devem sair da rede.

## Decisão
LLM e embeddings via **Ollama** local (`NEXO_OLLAMA_URL`), modelos padrão `qwen2.5:7b-instruct` (chat) e
`bge-m3` (embeddings, 1024 dimensões). Acesso apenas por `apps.ia.provedores`. Provedor "falso"
determinístico para testes e demonstração. Indisponibilidade do LLM degrada para resposta extrativa.

## Alternativas consideradas
- **API externa (OpenAI/Anthropic/Azure):** rejeitado por padrão — dados sairiam da instituição; exigiria ADR específica com classificação de dados.
- **vLLM/llama.cpp direto:** viável, mais complexo de operar; pode entrar como provedor futuro.

## Consequências
- Requer máquina com memória suficiente (≥ 16 GB RAM para 7B quantizado; GPU recomendada).
- Trocar o modelo de embeddings exige migração de dimensão e `reindexar_semantica --todos`.
