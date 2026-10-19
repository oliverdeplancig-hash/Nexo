# ADR-026 — Especificação OpenAPI da API, restrita à TI e sem CDN

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
A API do Nexo era descrita só à mão em `docs/api/README.md`. Para a TI da instituição integrar outros
sistemas (SEI, painéis, automações) e para a fase de nuvem (ADR-019), faltava uma especificação lida por
ferramentas, sempre igual ao código.

## Decisão
- **drf-spectacular** gera a especificação **OpenAPI 3** a partir do próprio código:
  `GET /api/v1/esquema/` (YAML ou JSON) e `GET /api/v1/documentacao/` (Swagger UI).
- **Acesso só para quem administra permissões ou consulta a auditoria** (`admin_permissoes`,
  `ver_auditoria`). A especificação mostra rotas e formatos, nunca dados, mas não precisa ficar aberta.
- **Sem CDN**: as telas da documentação vêm do pacote `drf-spectacular-sidecar`, servidas pelo Nexo, em
  linha com a ADR-004 e com redes sem acesso à internet.
- Rotas feitas como funções (`@api_view`) aparecem com corpo JSON livre (`apps/comum/esquema.py`); os
  campos delas continuam descritos em `docs/api/README.md`. Versão da especificação = `nexo/versao.py`.
- Arquivo para quem não tem acesso ao sistema: `python manage.py spectacular --file openapi.yaml`.

## Alternativas consideradas
- **Manter só a documentação manual**: desatualiza com facilidade e não serve para gerar clientes.
- **drf-yasg**: mantém só OpenAPI 2.0.
- **Swagger UI por CDN**: dependência externa e vazamento de metadados de navegação; recusado.

## Consequências
- Duas dependências novas (pacotes Python puros); as telas exigem `collectstatic` (o instalador já roda).
- Avisos de tipo em alguns campos calculados (mostrados como texto) podem ser refinados com anotações.
