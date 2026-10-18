# 02 — Architecture Rules

Regras arquiteturais obrigatórias. Cada regra tem código `RA-NN` e aponta para a ADR que a fundamenta.

| Código | Regra | ADR |
|---|---|---|
| RA-01 | Monólito modular Django; apps por domínio, sem dependência circular entre apps de domínio | ADR-001 |
| RA-02 | Toda decisão de acesso documental passa por `apps.acesso.servico` (`decidir`, `pode`, `documentos_visiveis`) | ADR-005 |
| RA-03 | Busca e contexto da IA são filtrados por permissão **antes** do ranqueamento | ADR-005, ADR-006 |
| RA-04 | O assistente segue a ordem fixa: validação → motor determinístico → busca → evidência → LLM → fallback extrativo | ADR-003 |
| RA-05 | LLM e embeddings somente por `apps.ia.provedores`; novos provedores exigem ADR | ADR-004 |
| RA-06 | Tempo real somente por Django Channels; o servidor nunca envia dados a grupos compartilhados | ADR-002 |
| RA-07 | Arquivos fora da raiz web; download só pela view autorizada | ADR-005 |
| RA-08 | Auditoria somente-inserção, encadeada por hash, sem conteúdo de documentos ou conversas | ADR-007 |
| RA-09 | Processamento de documentos por fila em banco (`processar_fila`); sem broker obrigatório | ADR-006 |
| RA-10 | Frontend React + MUI como PWA única para desktop e celular; nada de API é guardado em cache offline | ADR-008 |

Detalhes em [camadas.md](camadas.md) e [seguranca.md](seguranca.md).
