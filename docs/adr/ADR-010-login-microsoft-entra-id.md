# ADR-010 — Login institucional pela conta Microsoft (Entra ID)

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Os servidores já têm conta institucional `@pm.ba.gov.br`, usada no webmail pela tela de login da Microsoft
(Microsoft 365 / Entra ID). Manter uma segunda senha no Nexo aumenta o suporte (redefinições), não acompanha
desligamentos e transferências feitos na conta institucional e enfraquece a segurança (senha reutilizada,
sem MFA). As contas locais continuam necessárias para a demonstração e para a instalação local.

## Decisão
- Login pela conta Microsoft com **OpenID Connect**, fluxo *authorization code* + **PKCE (S256)**, aplicativo
  confidencial registrado no Entra ID da instituição (`apps/contas/entra.py`).
- O `id_token` só é aceito após verificar **assinatura** (chaves publicadas pelo locatário), **emissor**,
  **público** (client id), **validade**, **nonce**, **locatário** (`tid`) e **domínio do e-mail**
  (`NEXO_ENTRA_DOMINIOS`). `state` protege contra CSRF no retorno; a tentativa expira em 10 minutos.
- Vínculo da conta pelo `oid` (campo `Usuario.id_externo`). No primeiro login: conta existente com o mesmo
  e-mail é vinculada; senão, se `NEXO_ENTRA_CRIAR_USUARIOS=true`, cria-se o usuário **sem senha local**, com o
  perfil padrão (`servidor`) e **sem setor** — vê só documentos de acesso geral até o administrador definir
  setor e perfis. Com `false`, só entra quem foi cadastrado antes.
- **Autorização continua no Nexo** (ADR-005): a Microsoft diz *quem* é o usuário; setor, perfis e
  classificação decidem *o que* ele acessa. Usuário inativo no Nexo não entra, mesmo autenticado na Microsoft.
- O login por usuário e senha do Nexo pode ser desligado (`NEXO_LOGIN_LOCAL=false`).
- Sem configuração (`NEXO_ENTRA_TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`), o botão não aparece.
- Toda tentativa, aceita ou recusada, vai para a auditoria (`LOGIN`, `metodo: microsoft`, motivo).

## Relação com a ADR-004 (nada sai da rede)
Só trafegam com a Microsoft dados de **identidade** (nome, e-mail, identificadores), que já estão no
Microsoft 365 da instituição. **Nenhum documento, pergunta ou resposta** é enviado. O servidor do Nexo precisa
de saída HTTPS para `login.microsoftonline.com`.

## Alternativas consideradas
- **LDAP/Active Directory local:** exige acesso de rede ao controlador de domínio e conta de serviço; o
  Nexo receberia a senha do servidor. Pode ser outro provedor, por nova ADR, se a TI preferir.
- **gov.br:** identifica o cidadão, não o vínculo funcional com a instituição.
- **SAML 2.0:** equivalente em segurança, mais complexo de configurar e testar que OIDC.
- **Biblioteca pronta (MSAL, mozilla-django-oidc):** o fluxo é curto; implementação própria com PyJWT evita
  dependência extra e deixa a validação explícita e testada.

## Consequências
- O servidor entra com a mesma conta do e-mail, com MFA e políticas de acesso condicional da instituição.
- Desligamento na conta Microsoft impede novos logins; a sessão aberta do Nexo dura até 8 h
  (`NEXO_SESSAO_SEGUNDOS`). Para corte imediato, desativar o usuário no Nexo.
- Depende de a TI registrar o aplicativo no Entra ID (passo a passo em `docs/security/login-microsoft.md`).
- Backlog: mapear grupos do Entra ID para perfis e setores do Nexo; logout único (front-channel logout).
