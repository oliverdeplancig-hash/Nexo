# Banco de dados

PostgreSQL 15+ com extensões **vector** (pgvector ≥ 0.5, para HNSW) e **unaccent**.
A migração `comum/0001_extensoes` cria as extensões e a configuração de busca `nexo_pt`
(português + unaccent). Sem privilégio para `CREATE EXTENSION`, peça ao DBA:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS unaccent;
```

Instalação do pgvector: Linux `apt install postgresql-15-pgvector`; Windows: binários do projeto pgvector
ou compilação com Visual Studio (ver https://github.com/pgvector/pgvector#windows).

## Modelo principal

| Tabela | Conteúdo |
|---|---|
| `organizacao_setor` | Setores e dados do diretório |
| `contas_usuario`, `contas_perfil` | Usuários (setor, perfis) e perfis (funções) |
| `documentos_documento` | Metadados, arquivo, classificação, status, versão (`versao_anterior`) |
| `documentos_trecho` | Texto, página, seção, `busca` (tsvector, GIN), `embedding` (vector(1024), HNSW cosseno) |
| `documentos_colecao`, `_favorito`, `_acessorecente`, `_categoria` | Organização pessoal e institucional |
| `acesso_autorizacaodocumento` | Autorizações explícitas (usuário/setor/perfil, ações, validade) |
| `ingestao_etapaprocessamento` | Histórico das etapas de cada documento |
| `motor_regra`, `_fonteregra`, `_versaoregra` | Regras do motor, fontes e versões publicadas |
| `conversas_conversa`, `_mensagem` | Histórico (fontes e rastro em JSON) |
| `auditoria_eventoauditoria` | Trilha encadeada (somente inserção, protegida por gatilho) |
| `notificacoes_notificacao` | Notificações por usuário |
