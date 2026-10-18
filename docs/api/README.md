# API

Base: `/api/v1/`. Autenticação por sessão; escrita exige cabeçalho `X-CSRFToken`.
Paginação: `?page=N&tamanho=M` → `{count, next, previous, results}`.

## Autenticação
| Método | Rota | Descrição |
|---|---|---|
| GET | `auth/csrf/` | Emite cookie CSRF |
| POST | `auth/entrar/` | `{usuario, senha}` (403 se `NEXO_LOGIN_LOCAL=false`) |
| GET | `auth/provedores/` | Formas de entrada ativas: `{senha_local, microsoft: {ativo, rotulo}}` |
| GET | `auth/microsoft/?destino=/caminho` | Redireciona para o login Microsoft (ADR-010) |
| GET | `auth/microsoft/retorno/` | Retorno da Microsoft; cria a sessão e redireciona ao destino, ou a `/entrar?erro=<código>` |
| POST | `auth/sair/` | Encerra a sessão |
| GET | `auth/eu/` | Usuário, setor, perfis e funções |

## Documentos e acesso
| Método | Rota | Descrição |
|---|---|---|
| GET | `documentos/` | `aba=todos\|meus\|favoritos\|recentes\|compartilhados`, `q`, `tipo`, `setor`, `categoria`, `colecao`, `de`, `ate`, `ordem` |
| GET/PATCH/DELETE | `documentos/{id}/` | Detalhe (registra acesso) · editar · arquivar |
| GET | `documentos/{id}/arquivo/[?download=1]` | Arquivo (visualizar/baixar), auditado |
| GET | `documentos/{id}/conteudo/[?pagina=N]` | Trechos para visualização textual |
| POST/DELETE | `documentos/{id}/favorito/` | Favoritar |
| GET | `documentos/{id}/referencia/` | Referência para copiar |
| POST | `documentos/{id}/compartilhar/` | `{usuario\|setor\|perfil, acoes, valido_ate, motivo}` |
| GET | `acesso/documentos/{id}/minhas/` | Ações do usuário e motivos |
| GET/POST | `acesso/documentos/{id}/matriz/` | Matriz de autorizações · conceder |
| DELETE | `acesso/autorizacoes/{id}/` | Revogar |
| GET/POST | `colecoes/` · GET `categorias/` | Coleções e categorias |

## Ingestão
| Método | Rota | Descrição |
|---|---|---|
| POST | `ingestao/importar/` | multipart: `arquivos[]` + metadados + `setores_autorizados[]`, `perfis_autorizados[]` |
| GET | `ingestao/fila/` | Envios do usuário com etapas |
| POST | `ingestao/documentos/{id}/nova-versao/` | multipart `arquivo` |
| POST | `ingestao/documentos/{id}/reprocessar/` | Reprocessa |

## Busca, setores, motor, conversas, auditoria
| Método | Rota | Descrição |
|---|---|---|
| GET | `busca/?q=&modo=hibrida\|texto\|semantica\|nome` | Resultados agrupados por documento + facetas |
| GET | `setores/` · `setores/quem-pode-ajudar/?pergunta=` | Diretório e roteamento |
| CRUD | `motor/regras/` · POST `{id}/publicar/` · GET `{id}/versoes/` · POST `simular/` | Motor determinístico |
| GET | `conversas/` · `conversas/{id}/mensagens/` | Histórico |
| POST | `conversas/perguntar/` | `{texto, conversa_id?, documento_id?}` sem streaming |
| PUT · DELETE | `mensagens/{id}/avaliacao/` | `{util, motivo?, comentario?}` — só o autor, só respostas do assistente |
| GET | `avaliacoes/motivos/` | Motivos de "não útil" |
| GET | `lacunas/?situacao=pendentes\|tratadas\|todas&tipo=todas\|negativas\|sem_resposta&dias=90&q=` | Lacunas do assistente (exige `gerir_regras`); sem autor e sem texto da resposta |
| GET | `lacunas/resumo/?dias=30` | Indicadores: respostas, por origem, avaliações, lacunas pendentes |
| POST · DELETE | `lacunas/{id}/tratar/` | `{regra?, observacao?}` marca como tratada; DELETE reabre (auditado) |
| GET | `auditoria/eventos/` · `tipos/` · `integridade/` | Trilha |
| GET/POST | `notificacoes/` · `contagem/` · `{id}/ler/` · `ler-todas/` | Notificações |
| CRUD | `usuarios/`, `perfis/` · GET `funcoes/` | Administração |
| GET | `saude/` · `status/` | Monitoramento |

## WebSocket `/ws/chat/`
Cliente → `{"tipo":"mensagem","texto","conversa_id?","documento_id?"}`, `{"tipo":"interromper"}`, `{"tipo":"ping"}`.
Servidor → `pronto`, `conversa`, `pergunta_registrada`, `status` (`analisando`, `consultando_fontes`, `gerando`),
`token`, `aviso` (`ia_indisponivel`), `resposta`, `erro`, `pong`. Fechamento `4401` = sessão inválida.

## WebSocket `/ws/eventos/`
Servidor → `notificacao`, `processamento` (progresso da ingestão do próprio usuário).

## Manutenção
| Método | Caminho | Descrição |
|---|---|---|
| GET | `manutencao/copias/` | Situação das cópias de segurança (exige `admin_permissoes`). Criar e restaurar: comando `copia_seguranca` |

## Coleções
| Método | Caminho | Descrição |
|---|---|---|
| GET · POST | `colecoes/` | Lista (pessoais da pessoa + institucionais) e cria `{nome, descricao, pessoal, superior?}`. Institucional exige `gerir_colecoes` |
| GET · PATCH · DELETE | `colecoes/{id}/` | Detalhe, edição (`pessoal` não muda) e exclusão (os documentos continuam no repositório). Pessoal: só quem criou; institucional: `gerir_colecoes` |
| POST | `colecoes/{id}/documentos/` | `{documentos: [ids]}` inclui só os que a pessoa pode consultar → `{adicionados, ignorados}` |
| DELETE | `colecoes/{id}/documentos/{documento_id}/` | Tira o documento da coleção |
| GET | `documentos/?colecao={id}` | Documentos da coleção visíveis para a pessoa |
