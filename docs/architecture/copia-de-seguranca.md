# Cópia de segurança e restauração

Decisão: [ADR-011](../adr/ADR-011-copia-de-seguranca.md). Código: `backend/apps/manutencao/`.

## O que é copiado
Um único arquivo `nexo-AAAAMMDD-HHMMSS.nexobak` com:

| Item | Conteúdo |
|---|---|
| `banco.dump` | todo o banco (`pg_dump` formato custom): documentos, trechos e vetores, usuários, permissões, regras, conversas, avaliações e a **trilha de auditoria** |
| `arquivos/` | os arquivos originais dos documentos (`NEXO_ARMAZENAMENTO_DIR`) |
| `manifesto.json` | data, versões do PostgreSQL, extensões, migrações e o **SHA-256 de cada item** |

Com `NEXO_BACKUP_SENHA`, o pacote inteiro é **cifrado** (AES-256-GCM, chave derivada da senha com scrypt).
Ao lado fica `<nome>.nexobak.json` com dados não sensíveis (data, tamanho, SHA-256) usados na listagem.

Não entram: o `.env` (segredos — guarde à parte), o código (está no Git), os modelos do Ollama (baixam de
novo) e o idioma do OCR.

## Configuração (`backend/.env`)
| Variável | Padrão | Uso |
|---|---|---|
| `NEXO_BACKUP_DIR` | `backend/copias` | pasta das cópias (servidor: `/var/lib/nexo/copias`) |
| `NEXO_BACKUP_SENHA` | — | senha que cifra as cópias; **obrigatória em produção** |
| `NEXO_BACKUP_RETENCAO` | `14` | cópias diárias mantidas (as mais antigas são apagadas) |
| `NEXO_PG_BIN` | — | pasta do `pg_dump`/`pg_restore`/`psql`, se não estiverem no PATH |
| `NEXO_BACKUP_ALERTA_HORAS` | `30` | idade máxima da última cópia antes do alerta no painel |

> **A senha precisa ficar guardada fora do servidor** (cofre de senhas da TI, envelope lacrado etc.).
> Sem ela nenhuma cópia cifrada pode ser aberta — nem pelo Nexo, nem por ninguém.

## Agendar
- **Servidor Linux:** `nexo-copia.timer` (todo dia às 02:30; se o servidor estava desligado, roda ao ligar).
  `systemctl list-timers nexo-copia.timer` mostra a próxima execução; `journalctl -u nexo-copia` o resultado.
- **Windows:** dê duplo clique em `scripts\agendar-copia-windows.cmd` (padrão 12:30; outro horário:
  `agendar-copia-windows.cmd 18:00`). Ele pede a senha das cópias na primeira vez, agenda a tarefa
  "Nexo - copia de seguranca" e faz uma cópia de teste. Cópia avulsa: `scripts\copia-seguranca.cmd`.

**Leve as cópias para fora da máquina.** Uma cópia no mesmo disco não protege contra falha do disco,
roubo ou ransomware. No servidor, combine com a TI a cópia de `/var/lib/nexo/copias` para outro servidor ou
fita; no Windows, aponte `NEXO_BACKUP_DIR` para um disco externo ou pasta de rede. Como o pacote é cifrado,
pode ser guardado em local de menor confiança.

O painel **Administração → Cópias de segurança** (perfil com `admin_permissoes`) mostra as cópias e alerta
quando a última passou do limite ou quando estão sendo feitas sem cifra.

## Comandos
```bash
python manage.py copia_seguranca criar            # cópia agora
python manage.py copia_seguranca listar
python manage.py copia_seguranca verificar ARQUIVO  # confere tudo sem alterar nada
python manage.py copia_seguranca restaurar ARQUIVO --confirmar
```
Cópia feita com outra senha: `--senha` ou a variável `NEXO_BACKUP_SENHA_RESTAURACAO`.

## Restaurar
A restauração **substitui todo o banco e todos os arquivos** pelo conteúdo da cópia.

1. Pare o Nexo (servidor: `systemctl stop nexo-web nexo-ingestao nexo-copia.timer`; Windows: o próprio
   `scripts\restaurar-windows.cmd` faz isso e mostra a lista de cópias para escolher).
2. `python manage.py copia_seguranca restaurar /var/lib/nexo/copias/nexo-....nexobak --confirmar`
3. Inicie o Nexo de novo (servidor: `systemctl start nexo-web nexo-ingestao nexo-copia.timer`).

O que o comando faz, nesta ordem:
1. Lê o pacote inteiro e confere o SHA-256 de cada item (senha errada, arquivo cortado ou alterado → para
   sem alterar nada).
2. Recusa cópia de versão **mais nova** do Nexo; cópia mais antiga é aceita e o `migrate` roda no final.
3. Recusa se houver outras conexões no banco (Nexo ainda rodando). `--forcar` ignora essa checagem.
4. Faz uma cópia do estado atual (`nexo-antes-restauracao-...`) — para desfazer, restaure essa cópia.
   `--sem-copia-previa` pula esta etapa e, nesse caso, mantém a pasta de arquivos anterior renomeada.
5. Restaura o banco numa **única transação**: se algo falhar, o banco fica exatamente como estava.
   As extensões (pgvector, unaccent) são preservadas; não é preciso ser superusuário do PostgreSQL.
6. Troca a pasta de arquivos pela da cópia.
7. Verifica a cadeia da auditoria e registra o evento `RESTAURACAO` (que entra na cadeia restaurada).

### Restaurar em servidor novo
Instale o Nexo (`scripts/instalar-servidor.sh`), configure o `.env` (mesma `NEXO_BACKUP_SENHA`), rode
`migrate` uma vez (cria as extensões) e restaure a cópia.

## Teste de restauração (mensal)
Uma cópia só vale se restaura. Uma vez por mês:
1. `copia_seguranca verificar` na cópia mais recente **e** numa cópia guardada fora do servidor.
2. A cada trimestre, restaure numa máquina de homologação e confira: login, um documento abrindo, uma busca
   e o painel de auditoria ("Verificar integridade").
3. Registre a data e o resultado.

## Segurança
- Pacotes cifrados; credenciais do banco passam por variáveis de ambiente (não aparecem na lista de
  processos); itens do pacote com caminho suspeito (`..`, absoluto) são recusados.
- `COPIA_SEGURANCA` (sucesso ou falha) e `RESTAURACAO` ficam na auditoria.
- A pasta de cópias tem o mesmo nível de sigilo do banco: acesso só da conta `nexo` e da equipe de TI.
