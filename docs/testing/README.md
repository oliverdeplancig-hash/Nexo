# Testes

```bash
cd backend
python -m pytest            # usa nexo.settings_teste (provedor de IA falso, determinístico)
python -m pytest --create-db   # após mudar migrações
```

Requer PostgreSQL com pgvector (o banco de teste é criado automaticamente). 125 testes cobrem:

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

Frontend: `npm run build` (checagem de tipos).

## Avaliação da qualidade das respostas (ADR-025)

```bash
cd backend
python manage.py avaliar_respostas avaliacao/exemplo-demonstracao.json            # fictício, roda na CI
python manage.py importar_pasta "<pasta com os documentos>" --usuario <login> --setor <sigla> --classificacao geral
python manage.py avaliar_respostas avaliacao/local/<conjunto>.json --saida avaliacao/local/resultados
```

Mede, para cada pergunta de referência: fonte esperada citada (e posição), conteúdo esperado nos trechos
encontrados e na resposta, recusa correta para perguntas fora do acervo, origem e tempo. Formato do
conjunto em `apps/conversas/avaliacao.py`. Conjuntos e relatórios com documentos reais ficam em
`backend/avaliacao/local/` (fora do Git). Para números de resposta válidos, rode com o Ollama
(`NEXO_IA_PROVEDOR=ollama`): com o provedor de teste a resposta só repete os trechos.

## Ponta a ponta e acessibilidade (ADR-017)

```bash
cd frontend
npm run e2e            # sobe backend (banco nexo_e2e zerado, dados de demonstração) e frontend sozinho
npm run e2e:relatorio  # abre o relatório da última execução
```

Requer PostgreSQL com pgvector; o banco é `E2E_DATABASE_URL` (padrão
`postgres://nexo:nexo@localhost:5432/nexo_e2e`, criado se não existir). Navegador Chromium do Playwright
(`npx playwright install chromium` na primeira vez).

| Arquivo | O que cobre |
|---|---|
| `e2e/perfis.spec.ts` | menu por perfil, rota administrativa recusada, senha errada |
| `e2e/assistente.spec.ts` | resposta aprovada com fonte; avaliação negativa chega às lacunas sem identificar o autor |
| `e2e/colecoes.spec.ts` | criar coleção, adicionar e remover documentos, excluir sem apagar documentos |
| `e2e/vigencia.spec.ts` | revogar tira da busca, faixa de revogação, restabelecer |
| `e2e/ajuda.spec.ts` | Ajuda por perfil, botão "?" contextual, busca sem acentos |
| `e2e/acessibilidade.spec.ts` | axe-core (WCAG 2.1 A/AA): violações sérias ou críticas reprovam, em 15 telas |
| `e2e/credenciais.spec.ts` | cadastro com senha gerada, troca obrigatória no 1º acesso, senha temporária deixa de valer |
| `e2e/celular.spec.ts` | smartphone: navegação inferior, menu, ajuda, sem rolagem horizontal |

## Integração contínua
`.github/workflows/ci.yml` roda a cada envio para `main` e em pull requests: backend (ruff + pytest),
frontend (tipos + build) e, se passarem, ponta a ponta. Só dados fictícios e IA falsa.
