# Segurança

O Nexo guarda documentos institucionais e registros de auditoria. Trate qualquer falha de segurança como
incidente da instituição.

## Como comunicar uma vulnerabilidade
- **Não abra issue pública** nem comente em pull request.
- Comunique ao responsável técnico pelo Nexo e à área de tecnologia da informação da instituição, pelos
  canais internos oficiais, com: o que foi encontrado, como reproduzir, onde (versão ou commit, ambiente) e
  o impacto percebido.
- Não acesse, copie nem altere dados além do necessário para demonstrar o problema. Não inclua documentos
  ou dados pessoais reais no relato.

## O que já é garantido pelo projeto
- Acesso a documentos decidido somente por `backend/apps/acesso/servico.py` (ADR-005), inclusive na busca
  e no assistente.
- IA somente local; nenhum dado institucional sai da rede (ADR-004).
- Auditoria somente-inserção encadeada por hash (ADR-007); cópias cifradas (ADR-011).
- Senhas nunca vão para logs nem para a auditoria (ADR-018); `.env`, cópias e certificados ficam fora do
  Git (`.gitignore` e verificação antes do commit).

Modelo de autorização: [docs/security/modelo-de-autorizacao.md](docs/security/modelo-de-autorizacao.md).

## Versões atendidas
Correções de segurança são feitas na versão mais recente (`main`). Veja o [CHANGELOG.md](CHANGELOG.md).
