# Requisitos

Fonte: "REPOSITÓRIO INSTITUCIONAL + ASSISTENTE VIRTUAL IA" e "Projeto Repositório Chat Governamental"
(cópias em `docs/referencias/`).

## Funcionais

| Código | Requisito | Tela | Implementação |
|---|---|---|---|
| RF-01 | Painel inicial com saudação, busca/pergunta, acesso rápido, conversas e documentos recentes, setores | 01 | `paginas/Dashboard.tsx` |
| RF-02 | Chat com estados (geração, pesquisa, sem resultado, falha, reconexão, sem fontes, documento indisponível), streaming e interrupção | 02 | `paginas/Chat.tsx`, `conversas/consumers.py` |
| RF-03 | "Fontes consultadas" com documento, tipo, página/seção, trecho, versão e botão de abrir quando autorizado | 02 | `componentes/Fontes.tsx` |
| RF-04 | Repositório em tabela/grade, abas, filtros, ordenação, paginação, seleção múltipla | 03 | `paginas/Repositorio.tsx` |
| RF-05 | Visualização com páginas, zoom, busca no documento, metadados e ações; "Perguntar à IA" com contexto restrito ao documento | 04 | `paginas/Documento.tsx` |
| RF-06 | Busca por nome, conteúdo e significado, com destaque, filtros e facetas que não revelam restritos | 05 | `busca/servico.py`, `paginas/Busca.tsx` |
| RF-07 | Diretório de setores e "Qual setor pode me ajudar?" | 06 | `organizacao/diretorio.py`, `paginas/Setores.tsx` |
| RF-08 | Importação múltipla com metadados, permissões, progresso e etapas 1–5 | 07 | `ingestao/`, `paginas/Importacao.tsx` |
| RF-09 | Usuários, perfis, matriz de permissões por documento, histórico | 08 | `contas/`, `acesso/`, `paginas/Administracao.tsx` |
| RF-10 | Auditoria com filtros e verificação de integridade | 09 | `auditoria/`, `paginas/Auditoria.tsx` |
| RF-11 | Motor determinístico com regras versionadas e simulador | — | `motor/`, `paginas/Regras.tsx` |
| RF-12 | Versões smartphone/tablet/desktop; PWA instalável | todas | ADR-008 |

## Não funcionais

| Código | Requisito |
|---|---|
| RNF-01 | Funcionar localmente e em servidor Linux sem Docker com PostgreSQL 15 |
| RNF-02 | Nenhum dado enviado a serviços externos de IA |
| RNF-03 | Acessibilidade: contraste AA ou superior, teclado, foco visível, `prefers-reduced-motion` |
| RNF-04 | Respostas com fonte verificável; nada de fontes simuladas |
| RNF-05 | Auditoria íntegra e verificável |
| RNF-06 | Português do Brasil, DD/MM/AAAA, 24 h |
