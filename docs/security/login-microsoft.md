# Login pela conta Microsoft institucional — guia para a TI

Decisão: [ADR-010](../adr/ADR-010-login-microsoft-entra-id.md). Quem executa: administrador do Microsoft
Entra ID da instituição (permissão de *Application Administrator* ou equivalente).

## 1. Registrar o aplicativo no Entra ID
1. Portal do Entra ID (entra.microsoft.com) → **Identidade → Aplicativos → Registros de aplicativo → Novo registro**.
2. Nome: `Nexo`. Tipos de conta: **somente contas deste diretório organizacional** (locatário único).
3. URI de redirecionamento — plataforma **Web**:
   - servidor: `https://<endereço do Nexo>/api/v1/auth/microsoft/retorno/`
   - teste no computador local: `http://localhost:5173/api/v1/auth/microsoft/retorno/`
   (a Microsoft só aceita `http` para `localhost`).
4. Anote, na tela **Visão geral**, o **ID do diretório (locatário)** e o **ID do aplicativo (cliente)**.
5. **Certificados e segredos → Novo segredo do cliente**. Copie o **valor** (aparece uma única vez) e anote a
   data de expiração — o login para de funcionar quando o segredo vence.
6. **Permissões de API**: as permissões delegadas `openid`, `profile` e `email` do Microsoft Graph bastam
   (`User.Read` vem por padrão e pode ficar). Conceda o consentimento do administrador.
7. Opcional: em **Aplicativos empresariais → Nexo → Propriedades**, marque *Atribuição necessária* para
   restringir o login aos usuários ou grupos atribuídos.

## 2. Configurar o Nexo (`backend/.env`)
```
NEXO_ENTRA_TENANT_ID=<ID do diretório (locatário)>
NEXO_ENTRA_CLIENT_ID=<ID do aplicativo (cliente)>
NEXO_ENTRA_CLIENT_SECRET=<valor do segredo>
NEXO_ENTRA_DOMINIOS=pm.ba.gov.br
NEXO_ENTRA_CRIAR_USUARIOS=true      # false = só entra quem já foi cadastrado no Nexo
NEXO_ENTRA_PERFIL_PADRAO=servidor
NEXO_LOGIN_LOCAL=true               # false depois que o login institucional estiver validado
```
Reinicie o Nexo. A tela de entrada passa a mostrar **Entrar com a conta Microsoft institucional**.
Use o ID do locatário em forma de GUID: assim o Nexo recusa tokens de qualquer outro locatário.

Se o endereço público do Nexo for diferente do que chega ao servidor (proxy reverso), defina
`NEXO_ENTRA_REDIRECT_URI` exatamente igual ao cadastrado no passo 1.3.

## 3. Depois do primeiro login
- O usuário criado automaticamente tem o perfil `servidor` e **nenhum setor**: vê apenas documentos de
  acesso geral. Em **Administração → Usuários**, defina setor e perfis.
- Contas que já existiam no Nexo com o mesmo e-mail são vinculadas no primeiro login e mantêm setor e perfis.
- Para bloquear alguém imediatamente, desative o usuário no Nexo (a sessão aberta dura até 8 horas).
- Tentativas recusadas aparecem na **Auditoria** (`Login`, resultado `FALHA`, com o motivo).

## Mensagens de erro na tela de entrada
| Código | Causa provável |
|---|---|
| `dominio` | E-mail fora de `NEXO_ENTRA_DOMINIOS` |
| `locatario` | Conta de outro locatário Microsoft |
| `sem_cadastro` | `NEXO_ENTRA_CRIAR_USUARIOS=false` e usuário não cadastrado |
| `inativo` | Usuário desativado no Nexo |
| `token_invalido` | Relógio do servidor errado, client id trocado ou token adulterado (ver auditoria) |
| `troca_codigo` | Segredo vencido/errado ou URI de redirecionamento diferente da cadastrada |
| `indisponivel` | Servidor sem acesso HTTPS a `login.microsoftonline.com` |
