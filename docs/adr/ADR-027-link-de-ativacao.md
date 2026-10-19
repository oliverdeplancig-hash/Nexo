# ADR-027 — Link de ativação no cadastro: a pessoa cria a própria senha

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Pela ADR-018, o cadastro gera uma senha temporária e a envia por e-mail (ou a mostra a quem cadastrou). A
própria ADR-018 registrou a evolução: um **link de ativação**, para que nenhuma senha passe pelo e-mail nem
pela tela do administrador. A recuperação de senha (ADR-024) trouxe o mecanismo de link assinado.

## Decisão
- Com o envio de e-mail configurado, o cadastro oferece, como **opção recomendada**, "Enviar link para a
  pessoa criar a senha". A conta é criada **sem senha utilizável** e a pessoa recebe um link de uso único
  que vale `NEXO_ATIVACAO_HORAS` (72 h). Pelo link (`/ativar-conta`) ela cria a senha.
- Para quem esqueceu a senha, o administrador também pode **enviar o link** em vez de gerar senha temporária
  (`POST usuarios/{id}/enviar-link/`). Reenviar invalida o link anterior.
- Token sem estado, com sal próprio, assinado pela chave secreta, calculado sobre a senha atual (uso único)
  e com validade própria. Limite de tentativas por endereço igual ao da recuperação.
- Auditoria: envio do link e ativação, sem senha. Sem SMTP, as opções da ADR-018 continuam iguais.
- Código: `apps/contas/ativacao.py`; telas em `paginas/RecuperarSenha.tsx` e Administração.

## Alternativas consideradas
- **Manter só a senha temporária**: a senha trafega por e-mail e quem cadastra pode vê-la.
- **Token gravado no banco**: permitiria listar convites pendentes; o token sem estado basta e não guarda
  segredos.

## Consequências
- Ninguém além da própria pessoa conhece a senha, desde o primeiro acesso.
- Até usar o link, a conta não entra; se o link expirar, o administrador reenvia.
