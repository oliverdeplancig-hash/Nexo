# ADR-023 — Saúde do sistema: painel, verificação por comando e avisos aos administradores

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Na fase 1 (ADR-019) o Nexo roda num computador da instituição, cuidado por quem administra o sistema e não
necessariamente por uma equipe de infraestrutura. As falhas que mais prejudicam são silenciosas: a cópia
diária que parou, o disco enchendo, o processador da fila que caiu (documentos importados que nunca ficam
disponíveis), o Ollama desligado ou sem o modelo, o certificado vencendo, o modo de depuração esquecido
ligado. Cada uma só aparecia em lugares diferentes, ou em lugar nenhum.

## Decisão
- **Verificações num só módulo** (`apps/manutencao/saude.py`), cada uma com situação `ok`, `atencao` ou
  `problema`, um resumo e o que fazer:
  configuração (versão, depuração, cookies, e-mail, forma de entrada), banco (versão, tamanho, extensões
  `vector` e `unaccent`), espaço em disco das pastas de documentos e de cópias (atenção abaixo de 15% livre,
  problema abaixo de 5%), cópias de segurança (idade da última e cifra, ADR-011), processamento de
  documentos (fila, falhas, erros em 7 dias e **sinal de vida** do processador), IA local (provedor, Ollama
  respondendo, modelos baixados, fila de geração da ADR-020) e certificado HTTPS do servidor Windows
  (vencimento, autoassinado).
- **Sinal de vida**: o processador da fila grava `SinalDeVida` a cada 30 s; sem sinal há mais de 3 min, o
  painel acusa.
- **Painel** em Administração → Saúde do sistema (`GET /api/v1/manutencao/saude/`), só para quem tem
  `admin_permissoes`; atualiza a cada minuto.
- **Comando** `manage.py verificar_saude` com saída de erro quando há problema, para a TI encaixar no
  monitoramento que já usa. `--avisar` dispara as notificações.
- **Avisos**: o processador da fila verifica a cada hora e notifica quem administra permissões sobre itens
  em **problema** (não sobre atenção), no máximo uma vez por dia por assunto, com link para o painel.
- **Privacidade**: só estados e números. Nada de conteúdo de documentos, nomes de pessoas, senhas ou
  caminhos completos de arquivos na API.
- **Versão** do sistema em `nexo/versao.py` (SemVer, ADR-022), mostrada no painel e não exposta na
  verificação pública `/api/v1/saude/`.

## Alternativas consideradas
- **Ferramenta de monitoramento externa** (Zabbix, Prometheus): a instituição pode já ter uma; o comando com
  código de saída permite integrar, mas o Nexo não pode depender dela num computador de unidade.
- **E-mail para os administradores**: depende do SMTP (ADR-018), que pode não estar configurado; a
  notificação interna sempre funciona. Pode ser acrescentado quando o SMTP estiver em uso.
- **Avisar também os itens em atenção**: geraria ruído diário (ex.: certificado autoassinado).

## Consequências
- Quem administra vê e é avisado das falhas silenciosas, com a ação recomendada.
- Tabela nova `manutencao_sinaldevida` (uma linha por processo).
- Os limites (15%/5% de disco, 3 min sem sinal, 30 dias de certificado) estão no código; se a instituição
  precisar, viram configuração.
