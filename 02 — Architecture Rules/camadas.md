# Camadas e dependências

```
frontend (React/MUI PWA)
   │ HTTP (DRF, sessão + CSRF)        │ WebSocket (Channels)
   ▼                                  ▼
views / consumers  ──►  serviços de domínio  ──►  modelos (ORM)  ──►  PostgreSQL + pgvector
                          │
                          ├─ acesso.servico        (motor de permissões)
                          ├─ motor.motor           (motor determinístico)
                          ├─ busca.servico         (busca híbrida)
                          ├─ ia.provedores / rag   (Ollama)
                          ├─ conversas.orquestrador
                          └─ auditoria.servico
```

- Views e consumers não contêm regra de negócio; chamam serviços.
- `comum` não depende de nenhum app de domínio.
- `acesso` não depende de `busca`, `motor`, `ia` ou `conversas`.
- `conversas.orquestrador` é o único ponto que combina motor, busca e IA.
