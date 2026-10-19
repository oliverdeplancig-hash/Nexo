# ADR-024 — Recuperação de senha pelo próprio usuário com link de uso único

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Com a ADR-018, quem esquecia a senha dependia do administrador para gerar outra. Com 100 pessoas na rede
(ADR-019, ADR-020) isso vira fila de pedidos e faz o administrador conhecer, ainda que por pouco tempo, a
senha de outra pessoa. A ADR-018 deixou a recuperação pelo próprio usuário para quando houvesse SMTP
institucional, com proteção contra descobrir quem tem conta.

## Decisão
- **"Esqueci minha senha"** na tela de entrada: a pessoa informa usuário ou e-mail e recebe um **link de uso
  único** que vale `NEXO_RECUPERACAO_MINUTOS` (60). Pelo link, cria a nova senha (regras do Django), as
  outras sessões são encerradas e chega um e-mail avisando da alteração.
- **Só aparece** com login local ligado e SMTP configurado (`/auth/provedores/` informa `recuperar_senha`).
  Conta da Microsoft (sem senha local), inativa ou sem e-mail não recebe link.
- **Não revela quem tem conta**: a resposta é sempre a mesma, e o e-mail é enviado fora da requisição (sem
  diferença de tempo). E-mail repetido em mais de uma conta não é usado para adivinhar a conta.
- **Token sem estado**: gerador de tokens do Django com sal próprio, assinado pela chave secreta e calculado
  sobre a senha atual — deixa de valer quando a senha muda (uso único) e quando expira. Nada é gravado.
- **Limites**: `NEXO_LIMITE_RECUPERACAO` (5 por hora por endereço, para pedir e para usar o link) e no máximo
  3 e-mails por hora por conta.
- **Auditoria** (`ADMIN_USUARIO`): pedido de recuperação e senha recuperada, sem a senha.
- Código: `apps/contas/recuperacao.py`; telas `/esqueci-senha` e `/redefinir-senha`.

## Alternativas consideradas
- **Enviar uma senha temporária nova por e-mail**: qualquer pessoa poderia invalidar a senha de outra só
  sabendo o usuário; o link não muda nada até ser usado.
- **Perguntas de segurança ou código por SMS**: frágeis, ou dependem de serviço externo (ADR-004).
- **Token gravado no banco**: permite revogar um a um, mas o token sem estado já é de uso único e expira.

## Consequências
- Menos pedidos ao administrador; a geração de senha pelo administrador (ADR-018) continua para quem não tem
  e-mail.
- A segurança passa a depender da caixa de e-mail institucional da pessoa; o link curto e o aviso de
  alteração reduzem o risco.
- O endereço no e-mail usa `NEXO_URL_PUBLICA` (ou o nome validado por `ALLOWED_HOSTS`).
