# Regras de negócio

| Código | Regra |
|---|---|
| RN-001 | Um documento só aparece em busca, listagem e IA depois de processado e com status **Disponível**. |
| RN-002 | Classificações: **Geral** (todos consultam e visualizam; download só se habilitado), **Setor** (membros do setor responsável consultam, visualizam e baixam), **Restrito** (somente autorizações explícitas). |
| RN-003 | Responsável pelo documento e quem o cadastrou têm todas as ações sobre ele. |
| RN-004 | Ações implicam outras: administrar ⇒ todas; editar/baixar/compartilhar ⇒ visualizar; visualizar ⇒ consultar. |
| RN-005 | Ninguém concede ação que não possui. Conceder "administrar" exige a função *admin_permissoes*. |
| RN-006 | Autorizações podem ter validade; vencidas deixam de valer sem intervenção. |
| RN-007 | Alterar classificação exige "administrar" sobre o documento. |
| RN-008 | Documentos não são apagados: são **arquivados**. Nova versão arquiva a anterior quando fica disponível e herda as autorizações explícitas. |
| RN-009 | O assistente responde primeiro por regra publicada do motor determinístico; regras em rascunho nunca respondem. |
| RN-010 | Editar regra publicada a devolve para rascunho; cada publicação gera versão imutável. |
| RN-011 | Se o fundamento de uma regra não é acessível ao usuário, a resposta mostra apenas o encaminhamento ao setor. |
| RN-012 | Sem evidência documental suficiente, o assistente informa e sugere setores do diretório; não inventa. |
| RN-013 | O histórico de conversas é privado do usuário; fontes são reavaliadas a cada leitura. |
| RN-014 | O canal de contato do setor pode ser restrito aos membros do próprio setor. |
| RN-015 | A auditoria registra quem, quando, o quê e o resultado — nunca o conteúdo de documentos ou o texto das perguntas. |
| RN-016 | Setores são desativados, nunca apagados. |
