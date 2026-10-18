# Modelo de autorização

## Camadas
1. **Autenticação** — sessão Django; login com limite de 10 tentativas/min por IP.
2. **Funções administrativas** (perfil → funções): importar documentos, gerir coleções, gerir regras,
   gerir setores, administrar usuários, administrar permissões (crítica), ver auditoria.
   Não concedem acesso a conteúdo.
3. **Acesso documental** — `apps/acesso/servico.py`:

| Fonte da permissão | Ações |
|---|---|
| Responsável ou quem cadastrou | todas |
| Classificação **geral** (documento disponível) | consultar, visualizar (+ baixar se `permite_download_geral`) |
| Classificação **setor**, usuário do setor responsável | consultar, visualizar, baixar |
| Autorização explícita vigente (usuário, setor do usuário, perfil do usuário) | ações concedidas + implicadas |

Implicações: administrar ⇒ todas; editar/baixar/compartilhar ⇒ visualizar ⇒ consultar.

## Garantias
- Lista, busca, facetas, IA e histórico usam `documentos_visiveis` (filtro **antes** de ranquear).
- Inacessível = 404. `is_superuser` ignorado.
- Compartilhar: só ações que o próprio usuário possui; "administrar" só com *admin_permissoes*.
- Atribuir perfil com função crítica exige *admin_permissoes*.
- Fontes de mensagens antigas são reavaliadas a cada leitura.
- WebSocket: origem validada, sessão exigida, usuário recarregado por mensagem, sem grupos compartilhados.
