# ADR-002 — Tempo real com WebSocket via Django Channels

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O chat precisa de respostas progressivas, status ("pesquisando documentos", "gerando resposta"),
interrupção e notificações de processamento. A análise prévia (Projeto Repositório Chat Governamental)
comparou WebSocket nativo e Socket.IO.

## Decisão
WebSocket nativo com **Django Channels** em `/ws/chat/` e `/ws/eventos/`. Channel layer em memória na
instalação local; **Redis** (`NEXO_REDIS_URL`) quando houver mais de um processo. Reconexão com backoff
exponencial e batimento implementados no cliente (`src/api/socket.ts`). Endpoint REST
`/conversas/perguntar/` como alternativa sem streaming.

## Alternativas consideradas
- **Socket.IO (python-socketio):** rejeitado — protocolo próprio e dependência extra sem necessidade.
- **SSE:** viável para o streaming, mas não cobre interrupção pelo mesmo canal; mantido como opção futura.
- **Polling:** rejeitado — latência e carga.

## Consequências
- Autenticação por sessão validada no `connect` e usuário recarregado a cada mensagem.
- Sem Redis, eventos do worker `processar_fila` não chegam ao navegador em tempo real; a tela de
  importação faz polling como fallback.
