# ADR-011 — Cópia de segurança e restauração em pacote único cifrado

**Status:** Proposta · **Data:** 2026-10-18 · **Autor:** Geverson Oliver (Arquiteto de Soluções)

## Contexto
O Nexo guarda o acervo documental da instituição em dois lugares que precisam andar juntos: o banco
PostgreSQL (metadados, trechos, vetores, permissões, regras, conversas e a trilha de auditoria encadeada) e a
pasta de arquivos originais. Restaurar um sem o outro gera documentos sem arquivo ou arquivos órfãos. O
sistema roda em Windows (PostgreSQL embutido) e em servidor Linux sem Docker, operado por equipe de TI que
pode não ter DBA dedicado. Os dados não podem sair da rede sem proteção (ADR-004).

## Decisão
- **Pacote único `.nexobak`** com `pg_dump` (formato custom), os arquivos e um manifesto com o SHA-256 de cada
  item, versões e migrações. Banco copiado antes dos arquivos (pode sobrar arquivo, nunca faltar).
- **Cifra AES-256-GCM em blocos** (chave por scrypt a partir de `NEXO_BACKUP_SENHA`), com número do bloco e
  marca de fim na autenticação: detecta senha errada, alteração, troca de blocos e arquivo cortado. Senha
  obrigatória quando `NEXO_DEBUG=false`.
- **Restauração em uma transação**: o esquema do Nexo é limpo e o dump carregado no mesmo `psql
  --single-transaction`; extensões são preservadas (não exige superusuário). O SQL é gerado e conferido antes
  da carga, para que uma falha do `pg_restore` nunca confirme carga parcial.
- Salvaguardas: verificação completa antes de tocar no banco; recusa de cópia de versão mais nova; recusa com
  o Nexo em uso; cópia automática do estado atual antes de restaurar; evento `RESTAURACAO` na auditoria.
- Agendamento pelo sistema operacional (systemd timer; Agendador de Tarefas do Windows), retenção de N cópias
  e painel de situação para o administrador. A restauração **não** é exposta na interface web: é destrutiva e
  exige o Nexo parado.

## Alternativas consideradas
- **Backup físico/PITR (pg_basebackup + WAL, pgBackRest, Barman):** menor perda de dados (minutos), mas exige
  DBA, configuração no PostgreSQL e não inclui os arquivos. Recomendado como camada adicional quando a TI
  tiver a infraestrutura; não substitui o pacote lógico, que é portátil entre Windows e Linux.
- **Arquivos dentro do banco (bytea/large objects):** um só backup, mas incha o banco e o dump.
- **Cópias separadas de banco e pasta (scripts do SO):** simples, mas sem verificação conjunta nem garantia de
  consistência entre as partes.
- **Cifra com GPG/age externos:** ferramentas a mais para instalar e operar nos dois ambientes.

## Consequências
- Perda máxima de dados = intervalo entre cópias (24 h no padrão). Para menos, somar PITR (backlog).
- A senha das cópias passa a ser um segredo crítico: perdida a senha, perdidas as cópias.
- O pacote ocupa aproximadamente o tamanho dos arquivos + o dump comprimido; a retenção limita o espaço.
- Backlog: envio automático para destino externo, PITR e teste de restauração automatizado.
