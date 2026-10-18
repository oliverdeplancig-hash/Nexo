# Visão geral da arquitetura

```
                ┌──────────────────────────── Navegador / PWA ─────────────────────────────┐
                │ React 18 + MUI · telas 01–09 · socket.ts (reconexão) · sem cache de API   │
                └───────────────┬───────────────────────────────┬──────────────────────────┘
                     HTTPS /api/v1 (sessão+CSRF)          WSS /ws/chat · /ws/eventos
                ┌───────────────▼───────────────────────────────▼──────────────────────────┐
                │                    Django 5 (ASGI · daphne)                               │
                │  contas · organizacao · documentos · acesso · busca · motor · ia ·         │
                │  conversas (orquestrador + consumer) · ingestao · auditoria · notificacoes │
                └───────┬──────────────────────┬───────────────────────────┬───────────────┘
                        │                      │                           │
              PostgreSQL 15+            Armazenamento protegido       Ollama (local)
       (dados, tsvector, pgvector,        (arquivos fora da web)   qwen2.5 · bge-m3
        auditoria encadeada)
                        ▲
                        │  manage.py processar_fila (worker de ingestão)
```

## Fluxo de uma pergunta

1. Cliente envia `{"tipo":"mensagem"}` pelo WebSocket.
2. Consumer recarrega o usuário (ativo?) e chama `orquestrador.executar`.
3. Conversa validada como do próprio usuário; documento de contexto, se houver, revalidado.
4. **Motor determinístico** (`apps/motor/motor.py`) — regra publicada casou? Resposta curada + fontes
   permitidas, sem LLM.
5. **Busca híbrida** restrita a `documentos_visiveis(usuario)`.
6. Sem evidência → "sem fontes suficientes" + setores sugeridos (diretório, determinístico).
7. **RAG**: trechos numerados → Ollama em streaming → citações validadas.
8. Ollama indisponível → resposta extrativa com os trechos.
9. Mensagem persistida com rastro; evento de auditoria sem conteúdo.

Detalhes em [ia-e-motor.md](ia-e-motor.md). Implantação em [implantacao.md](implantacao.md).

## Mapa de apps

| App | Responsabilidade |
|---|---|
| `comum` | Normalização de texto, paginação, permissões administrativas, saúde |
| `organizacao` | Setores e diretório "quem pode ajudar" |
| `contas` | Usuários, perfis, funções, login; comandos `inicializar_nexo` e `carregar_demo` |
| `acesso` | Motor de permissões e matriz de autorizações |
| `documentos` | Documentos, trechos, coleções, favoritos, download protegido |
| `ingestao` | Upload, extração, fatiamento, indexação, fila |
| `busca` | Busca híbrida e facetas |
| `motor` | Regras, versões, simulador e motor determinístico |
| `ia` | Provedores (Ollama, falso) e montagem de prompt RAG |
| `conversas` | Orquestrador, histórico, WebSocket do chat |
| `auditoria` | Trilha encadeada e verificação de integridade |
| `notificacoes` | Notificações persistidas e canal de eventos |
