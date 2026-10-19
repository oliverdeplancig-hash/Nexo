# ADR-019 — Implantação em fases: computador da instituição na rede local, depois nuvem governamental

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Neste primeiro momento o Nexo vai rodar num **computador Windows da instituição**, e os demais servidores
vão usá-lo **pela rede interna**, no navegador ou como aplicativo (PWA). No futuro o sistema vai para um
**servidor na nuvem** da instituição (órgão público, PMBA).

O modo local existente (`iniciar-windows.cmd`) atendia uma pessoa: Vite em modo de desenvolvimento, HTTP,
`NEXO_DEBUG=true`, usuários de demonstração e janelas abertas. Na rede isso não serve: o PWA e o login
Microsoft (ADR-010) exigem HTTPS, as senhas trafegariam em claro, o sistema pararia ao fechar a sessão do
Windows e o modo de depuração mostra detalhes internos.

## Decisão
**Fase 1 — computador da instituição na rede local (Windows):**
- Instalador único, como Administrador: `scripts\instalar-servidor-windows.cmd` (pode ser repetido para
  atualizar). Cria o ambiente Python, gera as telas (`npm run build`), grava o `.env` de produção
  (`NEXO_DEBUG=false`, chave secreta aleatória, nomes e IPs do computador, cookies seguros), migra o banco,
  roda `preparar_producao` (recusa modo de depuração e chave fraca; desativa os usuários `.demo`), gera o
  certificado, libera o firewall (perfis Domínio e Privado), impede o computador de dormir, registra a
  tarefa agendada **"Nexo - servidor"** (na inicialização, mesmo sem ninguém conectado) e cria o primeiro
  administrador com senha temporária (ADR-018).
- **Um único endereço e uma única porta**: o daphne fala **HTTPS na 443** e atende HTTP na 80 só para
  redirecionar (`apps/comum/https.py`). As telas compiladas são entregues pelo próprio Nexo (WhiteNoise e
  `apps.comum.views.aplicativo`), sem nginx nem IIS. Arquivos do Vite com hash ficam em cache permanente;
  `index.html` e `sw.js`, não.
- **Supervisor** `scripts\servidor-windows.ps1`: liga o PostgreSQL embutido, o Ollama (se configurado), o
  processador da fila e o servidor web, religa o que cair e registra em `scripts\servidor.log`. Parada
  ordenada: `scripts\parar-servidor-windows.cmd`. A restauração de cópia (ADR-011) para e religa a tarefa.
- **Certificado**: `gerar_certificado` cria um certificado autoassinado com o nome do computador, o nome DNS
  informado e os IPs. A TI distribui `nexo.cer` por política de grupo ou o substitui pelo certificado da
  autoridade interna. Nenhum serviço externo é usado.
- **Endereço estável**: a TI define IP fixo ou um nome DNS (ex.: `nexo.<unidade>.local`) para o computador.
- Cópia de segurança diária agendada (ADR-011), de preferência numa pasta de rede da TI.

**Fase 2 — nuvem governamental:**
- Servidor Linux sem Docker, como já previsto (`scripts/instalar-servidor.sh`, `deploy/systemd`, nginx com
  `NEXO_ATRAS_DE_PROXY=true`). A migração é **restaurar no novo servidor a cópia `.nexobak`** do computador
  da fase 1 (ADR-011): banco e arquivos, com verificação de integridade.
- A nuvem precisa respeitar a ADR-004: ambiente sob controle da instituição (nuvem de governo ou
  contratada com dados no Brasil e cláusulas de sigilo), **IA hospedada pela própria instituição** (Ollama
  ou equivalente em máquina com GPU) e nenhum dado institucional enviado a serviços de IA de terceiros.
  A escolha do provedor será registrada numa nova ADR.
- Para muitas pessoas ao mesmo tempo, ver ADR-020 (vários processos, Redis, dimensionamento da IA).

## Alternativas consideradas
- **IIS ou nginx no Windows como proxy**: mais uma peça para instalar e manter num computador comum; o
  daphne já fala TLS e o WhiteNoise entrega as telas.
- **HTTP sem TLS na rede interna**: senhas em claro e PWA/login Microsoft indisponíveis.
- **Docker Desktop no Windows**: exige virtualização e licença em órgãos grandes; Docker continua só para
  desenvolvimento.
- **Serviço do Windows (NSSM, pywin32)**: dependência extra; a tarefa agendada com reinício cobre o caso.
- **Ir direto para a nuvem**: depende de contratação e da escolha do provedor; a fase 1 coloca o sistema
  em uso agora sem retrabalho, pois a migração é uma restauração de cópia.

## Consequências
- O computador precisa ficar ligado, na rede e sem suspender; uma queda dele interrompe o acesso de todos.
- Certificado autoassinado mostra aviso até a TI distribuí-lo.
- Desempenho limitado ao hardware do computador, principalmente para a IA (ADR-020).
- Código e documentação: `scripts/instalar-servidor-windows.ps1`, `scripts/servidor-windows.ps1`,
  `apps/comum/https.py`, comandos `criar_administrador`, `preparar_producao` e `gerar_certificado`;
  [implantacao.md](../architecture/implantacao.md).
