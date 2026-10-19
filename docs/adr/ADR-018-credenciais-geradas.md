# ADR-018 — Senha gerada pelo Nexo, envio por e-mail e troca obrigatória no primeiro acesso

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Enquanto o login institucional (ADR-010) depende da TI, os usuários entram com conta local. O administrador
precisava inventar uma senha, digitá-la no cadastro e entregá-la pessoalmente; a senha ficava conhecida por
quem cadastrou e não havia como o servidor criar a sua. Também não havia troca de senha pelo próprio usuário
nem forma simples de atender quem esqueceu a senha.

## Decisão
- No cadastro, por padrão, o Nexo **gera uma senha temporária** forte (14 caracteres, maiúsculas, minúsculas,
  dígitos e símbolos, sem caracteres ambíguos, com `secrets`) e a **envia por e-mail** com o usuário e o
  endereço do Nexo. O administrador ainda pode definir a senha inicial manualmente.
- A senha temporária **vale por `NEXO_SENHA_TEMPORARIA_HORAS` (72 h)** e **obriga a troca no primeiro
  acesso**: até lá, a API só atende "quem sou eu", troca de senha e sair (middleware `ExigeTrocaDeSenha`), e
  o chat em tempo real recusa a conexão. Senha temporária expirada não entra.
- Senha definida ou redefinida pelo administrador também é provisória: só o próprio servidor conhece a senha
  definitiva.
- **Sem servidor de e-mail** (`NEXO_EMAIL_HOST` vazio), sem e-mail cadastrado ou com falha no envio, o
  cadastro não falha: a senha aparece **uma única vez** na tela de quem cadastrou, para entrega por outro
  meio. Ela nunca é gravada em claro, nunca vai para a auditoria nem para logs e não pode ser consultada
  depois.
- **Gerar nova senha** (quem esqueceu): ação do administrador, invalida a anterior imediatamente. Redefinir
  a senha de quem administra permissões exige a mesma função.
- **Alterar senha** no Perfil para qualquer usuário com conta local, exigindo a senha atual, com os
  validadores de senha do Django (mínimo de 10 caracteres etc.) e limite de tentativas. A sessão atual
  continua; as demais são encerradas. Conta só com login Microsoft troca a senha na Microsoft.
- Auditoria (`ADMIN_USUARIO`): emissão de credenciais (cadastro ou redefinição, com ou sem e-mail) e troca de
  senha, sempre sem a senha.
- E-mail pelo SMTP da própria instituição (configurável). Lógica em `apps/contas/credenciais.py`.

## Alternativas consideradas
- **Link de ativação de uso único** (a pessoa define a senha sem receber nenhuma por e-mail): mais seguro
  contra caixa de e-mail comprometida; exige token e página pública de ativação. Boa evolução; a senha
  temporária com expiração e troca obrigatória atende ao pedido atual com risco limitado.
- **Mostrar a senha só na tela, sem e-mail:** mantém o administrador como intermediário, como antes.
- **Recuperação de senha pelo próprio usuário ("esqueci minha senha"):** depende de e-mail confiável e de
  proteção contra enumeração de contas; fica para quando o SMTP institucional estiver em uso.

## Consequências
- Cadastro de novos usuários sem o administrador conhecer a senha definitiva.
- Credenciais trafegam por e-mail: o servidor SMTP deve ser o institucional, com TLS, e a senha expira.
- Com o login Microsoft ativo (ADR-010), o cadastro local passa a ser exceção (contas de apoio, testes).
- Backlog: link de ativação, "esqueci minha senha" e expiração periódica de senha, se exigida por política.
