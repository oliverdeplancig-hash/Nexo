# Modelo de autorização

## Camadas
1. **Autenticação** — sessão Django; login pela conta Microsoft institucional (ADR-010, ver
   [login-microsoft.md](login-microsoft.md)) ou por usuário e senha locais; limite de 10 tentativas/min por IP.
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

## Avaliações e lacunas do assistente (ADR-012)
- Só o autor da pergunta avalia a resposta (mensagem de outra pessoa → 404).
- A lista de lacunas (função `gerir_regras`) mostra a **pergunta**, a origem da resposta, a avaliação e o
  comentário — **sem o autor** (nem nome, nem setor) e **sem o texto da resposta**, que pode conter trechos de
  documentos que o gestor não pode ler. Documentos usados como fonte aparecem só se o gestor puder consultá-los
  (`decidir`, ADR-005).
- Apagar a conversa apaga a pergunta, a avaliação e a lacuna. Tratar ou reabrir lacuna gera evento
  `LACUNA_TRATADA` na auditoria.

## Coleções (ADR-013)
- Coleção agrupa documentos e **não concede acesso**: quem abre a coleção vê só os documentos autorizados
  para si (`documentos_visiveis`). Só entram numa coleção documentos que quem organiza pode consultar.
- Coleção pessoal: visível, editável e excluível só por quem criou; não aparece (nem pelo nome) para outras
  pessoas, inclusive na tela do documento e no filtro `?colecao=`. Coleção institucional: todos veem;
  alterar exige `gerir_colecoes`. Regras em `apps/documentos/colecoes.py` (ADR-013).
