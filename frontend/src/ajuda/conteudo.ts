/**
 * Conteúdo da Ajuda (ADR-014). Cada tópico aparece só para quem tem a função indicada em `funcao`
 * (sem `funcao`: para todos). `telas` liga o tópico às telas: o botão "?" abre a Ajuda já no
 * tópico da tela em que a pessoa está.
 *
 * Ao mudar uma tela, atualize o tópico correspondente.
 */

export interface Topico {
  id: string;
  titulo: string;
  resumo: string;
  passos?: string[];
  dicas?: string[];
  funcao?: string | string[];
  telas?: string[];
}

export interface Grupo {
  titulo: string;
  descricao: string;
  topicos: Topico[];
}

export const ROTULO_FUNCAO: Record<string, string> = {
  importar_documentos: "cadastrar e importar documentos",
  gerir_colecoes: "criar e organizar coleções institucionais",
  gerir_regras: "manter as respostas aprovadas do assistente (motor de respostas)",
  gerir_setores: "manter o diretório de setores",
  admin_usuarios: "administrar usuários",
  admin_permissoes: "administrar perfis, permissões e cópias de segurança",
  ver_auditoria: "consultar a auditoria",
};

export const GRUPOS: Grupo[] = [
  {
    titulo: "Primeiros passos",
    descricao: "O que é o Nexo e como se orientar.",
    topicos: [
      {
        id: "o-que-e",
        titulo: "O que é o Nexo",
        telas: ["/"],
        resumo:
          "O Nexo reúne as normas, os procedimentos e os manuais da instituição num só lugar e tem um assistente que responde com base nesses documentos, sempre mostrando de onde tirou a informação.",
        passos: [
          "Na página inicial, digite o que você procura no campo “Pesquisar ou perguntar”.",
          "Use o Assistente IA para perguntas em linguagem comum (“como solicito férias?”).",
          "Use o Repositório documental para navegar pelos documentos e a Busca para procurar por palavras ou assunto.",
          "Em Setores e contatos, descubra qual setor cuida de cada assunto.",
        ],
        dicas: [
          "Você só vê os documentos autorizados para o seu perfil e o seu setor. Se um documento não aparece, ele pode ser restrito: veja “Não encontro um documento”.",
          "No celular, o Nexo pode ser instalado como aplicativo: no navegador, use “Adicionar à tela inicial”.",
        ],
      },
      {
        id: "meu-perfil",
        titulo: "Meu perfil e o que posso fazer",
        telas: ["/perfil"],
        resumo:
          "Em Perfil (clique no seu nome, no canto inferior esquerdo) você vê seu setor, seus perfis de acesso e as funções que eles liberam.",
        dicas: [
          "Perfis e setor são definidos pela administração do Nexo. Se faltar alguma permissão para o seu trabalho, procure o administrador do sistema no seu órgão.",
          "Para sair, use o ícone ao lado do seu nome.",
        ],
      },
      {
        id: "senha",
        titulo: "Primeiro acesso e senha",
        telas: ["/perfil"],
        resumo:
          "Quando o seu acesso é criado, você recebe por e-mail (ou do administrador) o usuário e uma senha temporária. No primeiro acesso o Nexo pede que você crie a sua própria senha.",
        passos: [
          "Entre com o usuário e a senha temporária.",
          "Na tela “Crie a sua senha”, digite a senha temporária, a nova senha e repita a nova senha.",
          "Para trocar a senha depois, abra Perfil (clique no seu nome) e use “Alterar senha”.",
        ],
        dicas: [
          "A senha temporária vale por poucos dias. Se ela expirou ou você esqueceu a sua senha, peça uma nova ao administrador do sistema.",
          "A nova senha precisa ter pelo menos 10 caracteres, não pode ser só números nem parecida com o seu nome ou usuário.",
          "Ao trocar a senha, outras sessões abertas em outros computadores são encerradas.",
          "Quem entra pela conta Microsoft institucional troca a senha na própria conta Microsoft.",
        ],
      },
    ],
  },
  {
    titulo: "Encontrar informação",
    descricao: "Assistente, busca, repositório e setores.",
    topicos: [
      {
        id: "assistente",
        titulo: "Perguntar ao assistente",
        telas: ["/assistente", "/historico"],
        resumo:
          "O assistente responde só com base nos documentos que você pode consultar e sempre indica as fontes. Quando existe uma resposta aprovada pela instituição para a pergunta, ela vem primeiro, sem IA.",
        passos: [
          "Abra Assistente IA (ou Nova conversa) e escreva a pergunta com suas palavras.",
          "Leia a resposta e confira as “Fontes consultadas”: clique numa fonte para abrir o documento no trecho usado.",
          "Se o assistente oferecer opções (“Você quis dizer…”), escolha a que corresponde à sua dúvida.",
          "Quando a resposta indicar um setor responsável, use o contato informado para seguir com a demanda.",
        ],
        dicas: [
          "O selo no alto da resposta diz de onde ela veio: “Resposta aprovada” (regra da instituição), “Com fontes citadas” (IA com citações) ou “Confira com atenção”.",
          "“Como esta resposta foi obtida” mostra o caminho percorrido (regra, busca, IA).",
          "Para perguntar sobre um documento específico, abra o documento e use “Perguntar à IA sobre este documento”.",
          "Suas conversas ficam em Histórico de conversas. Só você as vê.",
          "Confira as fontes antes de tomar decisões administrativas: o assistente orienta, mas o documento oficial é que vale.",
        ],
      },
      {
        id: "avaliar-resposta",
        titulo: "Avaliar uma resposta (👍 / 👎)",
        telas: ["/assistente"],
        resumo:
          "Abaixo de cada resposta há os botões “Resposta útil” e “Resposta não ajudou”. Sua avaliação ajuda a equipe a melhorar o assistente.",
        passos: [
          "Clique em 👍 se a resposta resolveu sua dúvida.",
          "Clique em 👎, escolha o motivo (incorreta, incompleta, não respondeu, desatualizada, setor errado, outro) e, se quiser, escreva um comentário.",
          "Clique de novo no botão marcado para desfazer.",
        ],
        dicas: [
          "A equipe que mantém as respostas vê a pergunta e a avaliação, mas não vê quem perguntou. Mesmo assim, não escreva dados pessoais no comentário.",
        ],
      },
      {
        id: "busca",
        titulo: "Buscar documentos",
        telas: ["/busca"],
        resumo:
          "A Busca procura ao mesmo tempo no nome, no conteúdo e no significado dos documentos (encontra “licença para tratamento de saúde” mesmo que você digite “afastamento médico”).",
        passos: [
          "Abra Buscar documentos (atalho Ctrl+K) e digite o que procura.",
          "Escolha o modo de busca: palavra-chave, palavras exatas, nome do documento ou por significado.",
          "Refine com os filtros: tipo de arquivo, setor responsável, categoria e período.",
          "Abra o resultado ou use “Perguntar à IA sobre este resultado”.",
        ],
        dicas: [
          "Sem resultados? Use termos mais gerais, remova filtros ou pergunte ao assistente qual setor pode ajudar.",
          "Documentos revogados ficam fora da busca. Para encontrá-los, marque “Incluir documentos revogados” em Vigência.",
        ],
      },
      {
        id: "repositorio",
        titulo: "Navegar no repositório",
        telas: ["/repositorio"],
        resumo:
          "O Repositório documental lista os documentos autorizados para você, com abas para Todos, Meus documentos, Favoritos, Recentes e Compartilhados comigo.",
        passos: [
          "Filtre por nome ou número de referência, tipo, setor, vigência (vigentes ou revogados) e data de atualização.",
          "Clique no título das colunas para ordenar; alterne entre tabela e grade.",
          "Marque a caixa de seleção de vários documentos para adicioná-los aos favoritos ou a uma coleção de uma vez.",
          "Use o ícone de olho para visualizar e o de seta para baixar (quando permitido).",
        ],
      },
      {
        id: "documento",
        titulo: "Abrir e usar um documento",
        telas: ["/documentos"],
        resumo:
          "Na tela do documento você lê o original ou o texto extraído, vê os metadados (setor, categoria, versão, classificação) e as permissões que você tem sobre ele.",
        passos: [
          "Alterne entre “Original” e “Texto”; no texto, use a busca no documento e o zoom.",
          "Use “Perguntar à IA sobre este documento” ou “Resumir”.",
          "Na barra de ações: favoritar, adicionar à coleção, copiar referência, baixar e compartilhar (conforme suas permissões).",
        ],
        dicas: [
          "Documento revogado aparece com uma faixa vermelha no topo, com a data, o motivo e, quando houver, o documento que o substitui. Ele continua disponível para consulta histórica, mas o assistente não o usa.",
          "Documentos digitalizados são lidos por OCR. Quando isso acontece, um aviso indica que a leitura automática pode ter erros: confira no original.",
          "“Suas permissões” mostra exatamente o que você pode fazer com aquele documento.",
        ],
      },
      {
        id: "setores",
        titulo: "Descobrir qual setor ajuda",
        telas: ["/setores"],
        resumo:
          "Em Setores e contatos, descreva sua demanda em “Qual setor pode me ajudar?” e o Nexo indica os setores responsáveis, com competências, serviços e como solicitar.",
        dicas: [
          "Alguns setores mostram o canal de contato só para quem é do próprio setor. Nesse caso, siga a orientação de acesso exibida no cartão.",
        ],
      },
      {
        id: "nao-encontro",
        titulo: "Não encontro um documento",
        resumo:
          "Se um documento não aparece na busca nem no repositório, provavelmente ele é restrito a outro setor ou a pessoas autorizadas. O Nexo não mostra nem o título de documentos que você não pode consultar.",
        passos: [
          "Pergunte ao assistente “como solicitar acesso a um documento restrito?”.",
          "Solicite o acesso formalmente ao setor responsável pelo documento, com a justificativa.",
          "Depois de autorizado, o documento aparece em “Compartilhados comigo”.",
        ],
      },
      {
        id: "notificacoes",
        titulo: "Notificações",
        telas: ["/notificacoes"],
        resumo:
          "O sino avisa quando um documento que você enviou terminou de ser processado (ou falhou), quando alguém compartilhou um documento com você e, para quem mantém documentos, quando uma revisão está próxima ou atrasada. Use “Marcar todas como lidas” para limpar a lista.",
      },
    ],
  },
  {
    titulo: "Organizar",
    descricao: "Favoritos e coleções.",
    topicos: [
      {
        id: "favoritos",
        titulo: "Favoritos e recentes",
        telas: ["/repositorio"],
        resumo:
          "Clique na estrela de um documento para guardá-lo em Favoritos. Em Documentos recentes ficam os que você abriu nos últimos dias.",
      },
      {
        id: "colecoes",
        titulo: "Coleções (pastas)",
        telas: ["/colecoes"],
        resumo:
          "Coleções reúnem documentos de um mesmo tema. Uma coleção não muda quem pode abrir cada documento: quem abre a coleção vê só os documentos autorizados para si.",
        passos: [
          "Em Pastas e coleções, clique em “Nova coleção”, dê um nome e uma descrição.",
          "No repositório, selecione os documentos e clique em “Adicionar à coleção” (ou, na tela de um documento, use o ícone de pasta).",
          "Clique numa coleção para ver seus documentos. Ali você pode editar, excluir a coleção ou selecionar documentos e “Remover da coleção”.",
          "Para tirar um documento de uma coleção pela tela do documento, clique no × da coleção em “Coleções”.",
        ],
        dicas: [
          "Coleções pessoais só você vê, edita e exclui.",
          "Excluir uma coleção não apaga nenhum documento: eles continuam no repositório.",
        ],
      },
      {
        id: "colecoes-institucionais",
        titulo: "Coleções institucionais",
        funcao: "gerir_colecoes",
        telas: ["/colecoes"],
        resumo:
          "Com o seu perfil você também cria coleções institucionais, visíveis a todos os servidores (cada um vê só os documentos autorizados para si).",
        dicas: [
          "Ao criar, desligue “Coleção pessoal”. Depois de criada, uma coleção não muda de pessoal para institucional.",
          "Excluir uma coleção institucional a remove para todos. Os documentos continuam no repositório.",
        ],
      },
    ],
  },
  {
    titulo: "Gestão documental",
    descricao: "Cadastro de documentos e respostas aprovadas do assistente.",
    topicos: [
      {
        id: "importar",
        titulo: "Cadastrar e importar documentos",
        funcao: "importar_documentos",
        telas: ["/importacao"],
        resumo:
          "Em Importar documentos você envia PDF, DOCX, TXT, MD, HTML e imagens digitalizadas (PNG, JPG, TIFF), até 50 MB por arquivo, com os metadados e a classificação de acesso.",
        passos: [
          "Arraste os arquivos ou clique em “Selecionar arquivos”.",
          "Preencha os metadados. Título, palavras-chave e data podem ficar vazios: o Nexo sugere a partir do arquivo. Em “Próxima revisão”, informe quando o documento deve ser conferido de novo.",
          "Escolha o setor responsável e a classificação: Geral (todos os servidores), Restrito ao setor responsável, ou Restrito (somente autorizados por setor ou perfil).",
          "Defina o download: “Permitir download a todos” ou “Autorizados também podem baixar”.",
          "Clique em “Enviar para processamento” e acompanhe as etapas: arquivo recebido, extração de conteúdo, identificação de metadados, indexação para pesquisa e disponibilização.",
        ],
        dicas: [
          "Documentos digitalizados passam por OCR. Confira a qualidade da leitura na tela do documento.",
          "Se uma etapa falhar, a mensagem explica o motivo e há o botão “Tentar novamente”.",
          "Para atualizar um documento, abra-o e use “Enviar nova versão”: as versões anteriores ficam registradas.",
          "A classificação decide quem vê o documento em todo o Nexo (busca, assistente e coleções). Na dúvida, classifique de forma mais restrita.",
        ],
      },
      {
        id: "painel-acervo",
        titulo: "Painel do acervo",
        funcao: ["importar_documentos", "gerir_regras", "ver_auditoria"],
        telas: ["/painel-acervo"],
        resumo:
          "O Painel do acervo mostra a situação dos documentos que você pode consultar: quantos estão vigentes e revogados, revisões atrasadas e próximas, a situação de cada setor e os documentos mais consultados.",
        passos: [
          "Abra Painel do acervo, no grupo Governança do menu.",
          "Confira os indicadores no topo; “Revisões atrasadas” fica destacado quando há pendências.",
          "Na tabela por setor, veja onde se concentram revogações, atrasos e documentos sem data de revisão.",
          "Clique num documento da lista de revisões atrasadas para revisá-lo ou revogá-lo.",
          "Em “Mais consultados”, escolha o período (7, 30 ou 90 dias) para ver o que os servidores mais abrem.",
        ],
        dicas: [
          "Os números consideram só os documentos que o seu perfil pode consultar; documentos restritos a outros setores não entram nas contas.",
          "“Mais consultados” vem da auditoria e mostra apenas a quantidade de aberturas, nunca quem abriu.",
          "Documentos muito consultados e sem revisão programada são bons candidatos para ganhar uma data de revisão ou virar resposta aprovada no motor.",
        ],
      },
      {
        id: "vigencia",
        titulo: "Vigência e revisão de documentos",
        funcao: "importar_documentos",
        telas: ["/repositorio"],
        resumo:
          "Documentos têm vigência (vigente ou revogado) e podem ter revisão periódica. Quem pode editar o documento vê, na tela dele, os botões “Registrar revisão” e “Revogar”.",
        passos: [
          "Para ver o que precisa de revisão, abra Repositório documental → aba “Para revisar” (documentos que você mantém com revisão nos próximos 30 dias ou atrasada).",
          "Abra o documento e confira se continua válido. Se continua, clique em “Registrar revisão” e escolha a data da próxima.",
          "Se o conteúdo mudou, use “Enviar nova versão”: a nova versão conta como revisão.",
          "Se o documento deixou de valer, clique em “Revogar”, informe o motivo e, se houver, o documento que o substitui.",
          "Revogou por engano? Use “Restabelecer vigência”.",
        ],
        dicas: [
          "Quem mantém o documento recebe uma notificação 30 dias antes da revisão e, se atrasar, de novo a cada semana.",
          "Documento revogado sai do assistente e da busca padrão, mas continua no repositório. Regras do motor baseadas nele ganham o aviso “Fonte revogada: revise”, e quem mantém essas regras é notificado.",
          "Revogar, restabelecer e registrar revisão ficam na auditoria.",
        ],
      },
      {
        id: "motor",
        titulo: "Respostas aprovadas (motor de respostas)",
        funcao: "gerir_regras",
        telas: ["/motor"],
        resumo:
          "Regras são respostas aprovadas pela instituição. Quando uma pergunta corresponde a uma regra publicada, o assistente devolve exatamente o texto cadastrado, sem IA, com o selo “Resposta aprovada”.",
        passos: [
          "Em Motor de respostas → Regras, clique em “Nova regra”.",
          "Escreva várias perguntas de exemplo, como os servidores perguntariam de verdade (uma por linha).",
          "Use palavras-chave para reforçar, termos obrigatórios (todos precisam aparecer) e termos excludentes (se aparecer, a regra não responde).",
          "Escreva a resposta, as etapas (Título | Descrição) e indique o setor responsável e o documento que fundamenta a resposta.",
          "Salve como rascunho, teste no Simulador e clique em “Publicar”.",
        ],
        dicas: [
          "O Simulador mostra a pontuação de cada regra para uma pergunta e se ela responde, pede esclarecimento ou segue para a busca.",
          "Editar uma regra publicada a devolve para rascunho: ela só volta a responder depois de publicada de novo. Cada publicação gera uma versão.",
          "Quem não pode consultar o documento que fundamenta a regra recebe só o encaminhamento ao setor, sem o conteúdo.",
          "Regra cuja fonte foi revogada aparece com o aviso “Fonte revogada: revise”. Enquanto não for revisada, ela continua respondendo, mas com um alerta de revogação e o selo “Confira com atenção”. Atualize a resposta e troque a fonte pelo documento que substituiu a antiga.",
        ],
      },
      {
        id: "lacunas",
        titulo: "Lacunas do assistente",
        funcao: "gerir_regras",
        telas: ["/motor"],
        resumo:
          "Em Motor de respostas → Lacunas do assistente ficam as perguntas que não tiveram resposta nos documentos e as respostas avaliadas como não úteis, com os indicadores dos últimos 30 dias.",
        passos: [
          "Filtre por Pendentes, Tratadas ou Todas e pelo tipo de lacuna.",
          "Use “Criar regra” para abrir o editor já com a pergunta como exemplo.",
          "Se a pergunta quase foi respondida por uma regra, use “Incluir como exemplo em …”.",
          "Para resposta mal avaliada que veio de uma regra, use “Revisar …”.",
          "Quando nada precisar ser feito, use “Marcar como tratada”. É possível reabrir depois.",
        ],
        dicas: [
          "A lista não mostra quem perguntou nem o texto da resposta, para proteger o servidor e documentos restritos.",
        ],
      },
    ],
  },
  {
    titulo: "Administração",
    descricao: "Usuários, setores, perfis, permissões e cópias de segurança.",
    topicos: [
      {
        id: "usuarios",
        titulo: "Usuários",
        funcao: "admin_usuarios",
        telas: ["/administracao"],
        resumo:
          "Em Administração → Usuários você cadastra servidores, define setor e perfis, e ativa ou desativa contas. No cadastro, o Nexo pode gerar a senha e enviar o acesso por e-mail.",
        passos: [
          "Clique em “Cadastrar usuário” e preencha usuário, nome, e-mail institucional, setor e perfis.",
          "Em “Senha de acesso”, deixe “Gerar senha e enviar por e-mail” e clique em “Salvar e enviar acesso”.",
          "Confira a janela “Acesso criado”: ela confirma o envio ou mostra a senha para você entregar, se o e-mail não puder ser enviado. A senha aparece só nesse momento.",
          "Para quem esqueceu a senha, use o ícone de chave na linha do usuário (“Gerar nova senha”).",
        ],
        dicas: [
          "A senha gerada é temporária: vale por poucos dias e, no primeiro acesso, a pessoa cria a própria senha. Até lá, a linha mostra “Aguardando 1º acesso”.",
          "Quem entra pela conta Microsoft institucional pela primeira vez é criado com o perfil Servidor e sem setor: defina o setor para que veja os documentos do próprio setor.",
          "Para bloquear alguém imediatamente, desative o usuário.",
          "Atribuir perfis com funções críticas exige a função de administrar permissões.",
        ],
      },
      {
        id: "setores-gestao",
        titulo: "Diretório de setores",
        funcao: "gerir_setores",
        telas: ["/setores"],
        resumo:
          "Em Setores e contatos, use “Cadastrar setor” ou o lápis de um setor para manter competências, serviços, tipos de demanda, palavras-chave, horário e canal de contato.",
        dicas: [
          "As palavras-chave e competências ajudam o assistente a encaminhar perguntas ao setor certo.",
          "Desmarque “Contato visível para todos os servidores” para mostrar o canal só a quem é do setor.",
        ],
      },
      {
        id: "perfis",
        titulo: "Perfis e funções",
        funcao: "admin_permissoes",
        telas: ["/administracao"],
        resumo:
          "Em Administração → Perfis e funções você cria perfis e escolhe as funções administrativas de cada um. Funções não dão acesso a documentos: o acesso vem da classificação, do setor e das autorizações.",
        dicas: ["Toda alteração de perfil fica registrada na auditoria."],
      },
      {
        id: "permissoes-documento",
        titulo: "Permissões por documento",
        funcao: "admin_permissoes",
        telas: ["/administracao"],
        resumo:
          "Em Administração → Permissões por documento você vê e concede autorizações (consultar, visualizar, baixar, editar, compartilhar, administrar) a usuários, setores ou perfis, com prazo de validade.",
        dicas: ["Prefira autorizações com prazo. Concessões e revogações ficam na auditoria."],
      },
      {
        id: "copias",
        titulo: "Cópias de segurança",
        funcao: "admin_permissoes",
        telas: ["/administracao"],
        resumo:
          "Em Administração → Cópias de segurança você confere se a cópia diária do banco e dos arquivos está em dia, se está cifrada e quais cópias existem.",
        dicas: [
          "Criar e restaurar cópias é feito no servidor, com o Nexo parado (no Windows: scripts\\copia-seguranca.cmd e scripts\\restaurar-windows.cmd).",
          "Antes de restaurar, o estado atual é copiado automaticamente.",
          "Guarde a senha das cópias fora do servidor: sem ela nenhuma cópia pode ser aberta.",
        ],
      },
    ],
  },
  {
    titulo: "Auditoria",
    descricao: "Trilha de conformidade.",
    topicos: [
      {
        id: "auditoria",
        titulo: "Consultar a auditoria",
        funcao: "ver_auditoria",
        telas: ["/auditoria"],
        resumo:
          "Em Auditoria você consulta os eventos registrados (logins, aberturas e downloads de documentos, consultas ao assistente, mudanças de permissão, cópias de segurança e outros), com filtros por tipo, usuário, setor e resultado.",
        passos: [
          "Use os filtros para encontrar os eventos e abra os detalhes de cada um.",
          "Clique em “Verificar integridade” para conferir se nenhum evento foi alterado ou apagado.",
        ],
        dicas: ["A trilha só aceita inclusões: nem administradores conseguem alterar ou apagar eventos."],
      },
    ],
  },
];

/** Tópicos que a pessoa pode ver, conforme as funções do seu perfil. */
export function topicosPermitidos(tem: (f: string) => boolean): Grupo[] {
  const permitido = (t: Topico) => !t.funcao || (Array.isArray(t.funcao) ? t.funcao.some(tem) : tem(t.funcao));
  return GRUPOS.map((g) => ({ ...g, topicos: g.topicos.filter(permitido) })).filter((g) => g.topicos.length > 0);
}

/** Tópico da tela atual (o mais específico entre os permitidos). */
export function topicoDaTela(grupos: Grupo[], caminho: string): string | null {
  let melhor: { id: string; tamanho: number } | null = null;
  for (const g of grupos)
    for (const t of g.topicos)
      for (const tela of t.telas ?? []) {
        const casa = tela === "/" ? caminho === "/" : caminho === tela || caminho.startsWith(`${tela}/`);
        if (casa && (!melhor || tela.length > melhor.tamanho)) {
          melhor = { id: t.id, tamanho: tela.length };
        }
      }
  return melhor?.id ?? null;
}
