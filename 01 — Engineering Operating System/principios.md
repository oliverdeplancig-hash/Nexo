# Princípios

1. **Segurança antes de conveniência.** Nenhuma funcionalidade justifica expor documento a quem não tem
   permissão — nem em contagens, facetas, sugestões ou mensagens de erro.
2. **Determinístico primeiro.** O que pode ser respondido por regra aprovada não passa pela IA.
   A IA é a última camada, nunca a primeira.
3. **Fonte ou silêncio.** Toda resposta baseada em documentos mostra a fonte. Sem fonte suficiente,
   o sistema diz isso e encaminha ao setor.
4. **Rastreabilidade.** Toda decisão relevante (acesso, resposta, permissão) deixa rastro auditável,
   sem registrar conteúdo sensível.
5. **Local por padrão.** O sistema deve funcionar em um único computador e em servidor sem Docker,
   com os mesmos comandos.
6. **Simplicidade operacional.** Menos peças móveis: fila em banco em vez de broker, Redis opcional,
   nenhum serviço externo obrigatório.
7. **Português do domínio.** Identificadores do domínio em português (`Documento`, `Setor`, `decidir`);
   termos técnicos consagrados podem ficar em inglês.
