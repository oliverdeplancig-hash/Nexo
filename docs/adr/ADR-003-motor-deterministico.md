# ADR-003 — Motor determinístico antes da IA

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Respostas sobre procedimentos institucionais precisam ser exatas, repetíveis e auditáveis. LLMs são
probabilísticos e podem errar prazos e requisitos. Há perguntas recorrentes cuja resposta oficial é conhecida.

## Decisão
Toda pergunta passa primeiro pelo **motor determinístico** (`apps/motor`): regras curadas e publicadas
(frases de exemplo, palavras-chave, termos obrigatórios/excludentes, regex) com pontuação por
similaridade de radicais (Dice/contenção) sobre texto normalizado. Ordenação total
(pontuação, prioridade, código); limiar e margem de ambiguidade configuráveis; empate gera
desambiguação. Só sem regra aplicável a pergunta segue para busca e RAG. Toda resposta guarda o rastro.

## Alternativas consideradas
- **Somente RAG:** rejeitado — sem garantia de exatidão para procedimentos oficiais.
- **Classificador de intenções treinado:** rejeitado — não é determinístico nem auditável por servidores.
- **Árvores de decisão/fluxos rígidos:** rejeitado como única via — pouco flexível para linguagem natural.

## Consequências
- Gestores documentais mantêm regras (tela "Motor de respostas" com simulador e versões).
- Regras com fonte restrita mostram apenas encaminhamento (RN-011).
- Backlog: métricas de perguntas que caem no RAG para sugerir novas regras.
