# Ameaças e mitigações

| Ameaça | Mitigação |
|---|---|
| Vazamento de documento restrito pela IA | Contexto montado apenas de `documentos_visiveis`; teste `test_rag_cita_somente_documentos_autorizados` |
| Inferência de existência por contagens/facetas | Facetas calculadas sobre ids já autorizados; 404 em vez de 403 |
| Injeção de prompt em documento | Prompt do sistema trata trechos como dados; motor determinístico responde procedimentos críticos sem LLM |
| Citação inventada | Remoção de `[n]` fora do contexto; selo "Confira com atenção" sem citações |
| Sequestro de sessão/CSRF | Cookies HttpOnly/Secure/SameSite, CSRF em escrita, HTTPS em produção |
| WebSocket de outra origem | `AllowedHostsOriginValidator` |
| Upload malicioso | Lista de extensões, verificação de assinatura, limite de tamanho, nome aleatório, armazenamento fora da web, HTML servido com CSP sandbox |
| Adulteração da auditoria | Cadeia de hashes + gatilho que bloqueia UPDATE/DELETE + verificação |
| Cache de dados no celular | Service worker sem cache de `/api` |
| Escalada de privilégio administrativa | Funções críticas restritas e auditadas |
| Descobrir quem tem conta ou tomar conta pela recuperação de senha | Resposta sempre igual e envio fora da requisição; link de uso único, assinado e curto; limites por endereço e por conta; aviso de alteração por e-mail (ADR-024) |
| ReDoS em regras | Regex só por gestores, limite de 300 caracteres, validação na gravação |
