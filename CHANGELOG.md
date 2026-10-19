# Registro de mudanças

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/); versões seguem
[SemVer](https://semver.org/lang/pt-BR/) (ADR-022). Enquanto a versão for 0.x, o Nexo está em implantação
inicial e versões menores podem mudar comportamento.

## [Não lançado]
### Adicionado
- Servidor de rede no Windows: instalador como Administrador, HTTPS na 443 com redirecionamento da 80,
  telas entregues pelo próprio Nexo, tarefa agendada com supervisor, certificado autoassinado, primeiro
  administrador com senha temporária e verificação de produção (ADR-019).
- Capacidade para muitas pessoas ao mesmo tempo: fila da IA com aviso de posição e resposta imediata com
  trechos quando ela está ocupada, conjunto de conexões do banco, teste de carga (`manage.py teste_carga`),
  processos web extras no Linux e guia de dimensionamento (ADR-020).
- Modo de ensaio do servidor de rede (`instalar-servidor-windows.cmd teste`) e desinstalação sem perda de dados.
- Cadastro com link para a pessoa criar a própria senha, sem senha por e-mail; o administrador pode reenviar o
  link (ADR-027).
- Especificação OpenAPI em `/api/v1/esquema/` e documentação navegável em `/api/v1/documentacao/`, para a TI (ADR-026).
- Avaliação da qualidade das respostas (`manage.py avaliar_respostas`), carga do acervo por pasta
  (`manage.py importar_pasta`) e conjunto de referência na CI (ADR-025).
- "Esqueci minha senha": link de uso único por e-mail, sem revelar quem tem conta (ADR-024).
- Saúde do sistema: painel em Administração, `manage.py verificar_saude` e avisos diários aos administradores
  sobre cópias atrasadas, disco cheio, processador parado, IA fora do ar e certificado vencendo (ADR-023).
- Memória da conversa por compactação: o assistente entende perguntas de continuação (ADR-021).
- Governança do repositório: guia de contribuição, política de segurança, modelos de issue e PR,
  verificações antes do commit, atualização automática de dependências e cobertura mínima na CI (ADR-022).

### Corrigido
- O assistente respondia perguntas fora do acervo com trechos sem relação quando havia só uma palavra
  genérica em comum; agora exige cobertura mínima dos termos da pergunta (ADR-025).
- Palavras juntas no texto extraído de alguns PDFs ("POLÍCIAMILITARDABAHIA"): o texto passa a vir do pdfium.
- Etapas do assistente de todas as conversas abertas rodavam em fila numa única linha de execução.
- Pergunta esperando a IA segurava uma conexão do banco, deixando telas e motor lentos no pico.
- O nginx não passava o IP real ao daphne: auditoria e limite de login usariam o IP do proxy.

## [0.1.0] - 2026-10-19
Primeira versão completa para uso local e demonstração.
### Adicionado
- Repositório com controle de acesso por setor, perfil e documento (ADR-005), busca híbrida e ingestão de
  PDF, DOCX, TXT, MD e HTML (ADR-006), OCR local (ADR-009).
- Assistente com motor determinístico antes da IA local (ADR-003, ADR-004), fontes citadas e
  encaminhamento ao setor responsável; avaliação das respostas e painel de lacunas (ADR-012).
- Auditoria somente-inserção encadeada por hash (ADR-007); PWA responsiva (ADR-008).
- Login institucional Microsoft Entra ID (ADR-010); senha gerada, envio por e-mail e troca obrigatória
  no primeiro acesso (ADR-018).
- Cópia de segurança cifrada e restauração (ADR-011); coleções (ADR-013); Ajuda por perfil (ADR-014);
  vigência e revisão de documentos (ADR-015); painel do acervo (ADR-016).
- Testes de ponta a ponta com acessibilidade automática e integração contínua (ADR-017).
