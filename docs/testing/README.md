# Testes

```bash
cd backend
python -m pytest            # usa nexo.settings_teste (provedor de IA falso, determinístico)
python -m pytest --create-db   # após mudar migrações
```

Requer PostgreSQL com pgvector (o banco de teste é criado automaticamente). 106 testes cobrem:

| Área | Arquivo | Destaques |
|---|---|---|
| Texto | `comum/tests/test_texto.py` | normalização e radicais estáveis |
| Permissões | `acesso/tests/test_motor_permissoes.py` | propriedade filtro de banco ≡ decisão individual, para todas as ações |
| Motor | `motor/tests/test_motor.py` | determinismo, limiar, obrigatórios/excludentes, regex, desambiguação, prioridade, encaminhamento |
| Orquestrador | `conversas/tests/test_orquestrador.py` | RAG só com autorizados, sem evidência, conversa alheia, revogação, fallback extrativo |
| WebSocket | `conversas/tests/test_websocket.py` | conexão anônima recusada, streaming completo |
| API | `documentos/tests/test_api_documentos.py` | 404 para restritos, download auditado, importação, facetas |
| Ingestão | `ingestao/tests/test_extratores.py` | DOCX, HTML, OCR ausente, fatiamento estável |
| Auditoria | `auditoria/tests/test_auditoria.py` | cadeia, adulteração detectada, gatilho |

Frontend: `npm run build` (checagem de tipos). Verificação visual em 1440 px e 390 px.
