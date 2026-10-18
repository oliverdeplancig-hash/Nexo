# Regras de segurança (arquitetura)

1. Autenticação por sessão Django (cookie HttpOnly, SameSite=Lax) + CSRF em toda escrita.
2. WebSocket valida origem (`AllowedHostsOriginValidator`) e sessão no `connect`; o usuário é recarregado
   a cada mensagem — contas desativadas perdem acesso imediatamente.
3. Documento inacessível responde **404**, nunca 403, para não revelar existência.
4. `is_superuser` não dá acesso documental.
5. Funções administrativas (perfis) não dão acesso a conteúdo.
6. Conteúdo de documentos é tratado como **dado** no prompt; o prompt do sistema instrui a ignorar ordens
   contidas nos trechos (mitigação de injeção de prompt).
7. Respostas da IA só exibem citações `[n]` que existem no contexto entregue; as demais são removidas.
8. HTML enviado é servido com `Content-Security-Policy: sandbox`.
9. Service worker do PWA não armazena respostas da API nem arquivos.
