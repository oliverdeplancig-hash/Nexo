# Como contribuir com o Nexo

## Antes de começar
- Leia o [CLAUDE.md](CLAUDE.md) (hierarquia de regras), a [visão geral](docs/architecture/visao-geral.md) e as
  [ADRs](docs/adr/README.md). Mudança que contraria uma ADR aceita exige **nova ADR** que a substitua.
- Restrições que não se negociam: IA somente local (ADR-004), toda resposta passa primeiro pelo motor
  determinístico (ADR-003), acesso a documentos decidido só por `apps/acesso/servico.py` (ADR-005), nada de
  logotipos, nomes de órgãos, contatos ou fontes inventados.
- Nunca use dados institucionais reais em testes, exemplos, issues ou PRs: use os dados de demonstração.

## Ambiente
Passo a passo em [docs/architecture/implantacao.md](docs/architecture/implantacao.md). Depois:

```bash
pip install -r backend/requirements-dev.txt
pre-commit install          # verificações antes de cada commit (ruff, chaves, arquivos de senha)
```

## Fluxo
1. Crie um ramo a partir de `main` (`funcionalidade/…`, `correcao/…`).
2. Código e nomes em português, como o restante do projeto; organização por app de domínio em
   `backend/apps/<dominio>/` e por página/componente em `frontend/src/`.
3. **ADR automática**: funcionalidade nova ou mudança de comportamento com decisão ainda não registrada sai
   com a sua ADR no mesmo commit (`docs/adr/ADR-NNN-titulo.md`, status Proposta, índice atualizado).
   Correção de defeito que não muda decisão não precisa de ADR.
4. Testes: todo comportamento novo e todo defeito corrigido ganham teste. A CI exige a cobertura mínima de
   `backend/.coveragerc`.
5. Atualize a documentação afetada, a Ajuda (`frontend/src/ajuda/conteudo.ts`) quando mudar uma tela e a
   seção "Não lançado" do [CHANGELOG.md](CHANGELOG.md).
6. Commits em português, no imperativo ("Adiciona…", "Corrige…"), um assunto por commit.
7. Abra o PR pelo modelo; a CI (ruff, pytest, build, ponta a ponta e acessibilidade) precisa passar.

## Verificação local
```bash
cd backend && ruff check . && ruff format --check . && python -m pytest --cov
cd frontend && npm run build && npm run e2e
```

## Versões
SemVer: `MAIOR.MENOR.CORREÇÃO`. Ao publicar uma versão, mova "Não lançado" para a nova versão no
CHANGELOG e crie a tag `vX.Y.Z` no commit correspondente (ADR-022).
