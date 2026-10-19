# ADR-025 — Avaliação contínua da qualidade das respostas com perguntas de referência

**Status:** Proposta · **Data:** 2026-10-19 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
Os testes automáticos garantiam que o assistente **funciona** (permissões, fontes, streaming), mas não
mediam se ele **responde certo** com o acervo real. Sem medida, não há como saber se trocar o modelo de IA,
ajustar a busca ou criar regras do motor melhora ou piora as respostas, nem chegar ao piloto com segurança.

O primeiro conjunto real foi montado com documentos de processos do **Centro Corporativo de Projetos
(CCP/DEPLAN)**: manual de atribuições do DEPLAN, cadeia de valor, Modela DEPLAN, POP do PAD-e, POP Fundo a
Fundo, macroprocesso e TPP de eventos pedagógicos, árvore de documentos SEI e currículo do CIGProc.
Ficaram de fora conversas pessoais, planilhas com dados de pessoas e material de terceiros.

## Decisão
- **Conjunto de avaliação** em JSON: pergunta, documentos que devem ser citados, termos que a resposta deve
  (ou não deve) conter, se a pergunta está fora do acervo (deve dar "sem fontes") e a origem esperada.
- **`manage.py avaliar_respostas`** faz as perguntas pelo mesmo caminho do chat, como um usuário real (com
  as permissões dele), e mede: fonte esperada citada e em que posição, conteúdo esperado **nos trechos
  encontrados** (mede a busca sem depender do modelo) e **na resposta**, recusa correta, origem e tempo.
  Grava relatório em Markdown e JSON e falha abaixo de `--minimo`. Não deixa conversas no histórico.
- **Na CI**, um conjunto com os documentos **fictícios** de demonstração (`backend/avaliacao/exemplo-
  demonstracao.json`, mínimo de 80%) roda a cada mudança. Conjuntos e relatórios com documentos reais ficam
  em `backend/avaliacao/local/`, **fora do Git** (ADR-004, ADR-017).
- **`manage.py importar_pasta`** para a carga inicial do acervo real (mesmas validações, auditoria e
  permissões da tela de importação; pula arquivos repetidos).

Melhorias decididas a partir da primeira medição:
- **Evidência mínima por cobertura dos termos** (`busca.servico.evidencia_suficiente`): um trecho encontrado
  por texto só autoriza a resposta se cobrir ao menos `NEXO_COBERTURA_MINIMA` (50%) dos termos da pergunta,
  com peso pela raridade no acervo (como IDF), contando o título do documento e ignorando a moldura da
  pergunta ("o que significa", "quantos"). Antes, uma palavra genérica em comum ("deve", "PMBA") bastava, e o
  assistente respondia perguntas fora do acervo com trechos sem relação. A similaridade semântica
  (`NEXO_SIMILARIDADE_MINIMA`) continua valendo como evidência.
- **Texto de PDF pelo pdfium**, com o pypdf como reserva: o pypdf juntava palavras em vários PDFs
  institucionais ("POLÍCIAMILITARDABAHIA", "CentroAdministrativadaBahia").

## Resultados (contêiner de desenvolvimento, IA e embeddings de teste)
| Indicador (28 casos CCP/DEPLAN) | Antes | Depois |
|---|---|---|
| Fonte esperada citada | 100% | 96% |
| Conteúdo esperado nos trechos encontrados | 80% | 80% |
| Recusa correta fora do acervo | **0%** | **100%** |

A recusa correta é o ganho principal. O texto do pdfium não mudou os números neste conjunto (as páginas com
palavras juntas eram sobretudo capas e créditos), mas corrige o texto mostrado nas citações. Os números de
**resposta** dependem do modelo: com o provedor de teste a resposta só repete trechos, então o resultado
que vale para o piloto é o rodado no computador com Ollama (`qwen2.5` e `bge-m3`).

O conjunto fictício revelou ainda uma regra do motor incompleta: "alterar o período de férias" é respondido
pela regra geral de férias, que não traz o prazo de alteração. Esse tipo de achado orienta o ajuste das
regras pelos gestores (ADR-012).

## Alternativas consideradas
- **Avaliação por outro LLM ("LLM como juiz")**: mais flexível com respostas em texto livre, mas exige um
  modelo maior local (ADR-004) e é menos previsível; termos esperados e fontes são verificáveis e baratos.
- **Só avaliação humana pelas lacunas (ADR-012)**: continua, mas chega depois do problema; a avaliação de
  referência roda antes de cada mudança.

## Consequências
- Toda mudança de modelo, busca ou regras pode ser comparada com números.
- O conjunto real precisa ser mantido junto com o acervo (novas perguntas quando entram documentos).
- Mais perguntas são recusadas quando a busca só acha palavras genéricas; se aparecerem recusas indevidas,
  ajustar `NEXO_COBERTURA_MINIMA` e medir de novo.
