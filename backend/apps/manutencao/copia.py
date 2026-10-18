"""Cópia de segurança e restauração do Nexo: banco PostgreSQL + arquivos dos documentos (ADR-011).

Pacote `.nexobak` = arquivo tar (cifrado com AES-256-GCM quando há senha) contendo, nesta ordem:
    banco.dump          pg_dump em formato custom (comprimido)
    arquivos/...        conteúdo de NEXO_ARMAZENAMENTO_DIR
    manifesto.json      versões, migrações, extensões, contagens e o SHA-256 de cada item
Ao lado fica `<nome>.nexobak.json`, com metadados não sensíveis (data, tamanho, SHA-256 do pacote).

O banco é copiado antes dos arquivos: um documento incluído durante a cópia pode ter o arquivo sem o
registro (inofensivo), mas nunca o registro sem o arquivo.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db import connection, connections
from django.utils import timezone

from .cifra import ErroCifra, EscritorCifrado, LeitorCifrado, esta_cifrado

FORMATO = 1
EXTENSAO = ".nexobak"
ROTULO_AGENDADA = "nexo"
ROTULO_ANTES_RESTAURACAO = "nexo-antes-restauracao"
_PADRAO_AGENDADA = re.compile(rf"^{ROTULO_AGENDADA}-\d{{8}}-\d{{6}}{re.escape(EXTENSAO)}$")
_BLOCO = 1024 * 1024


class ErroCopia(Exception):
    """Falha com mensagem pronta para o operador."""


# --------------------------------------------------------------------------
# Configuração e ferramentas do PostgreSQL
# --------------------------------------------------------------------------
def config() -> dict:
    return settings.NEXO_BACKUP


def pasta_copias() -> Path:
    pasta = Path(config()["DIR"])
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta


def binario(nome: str) -> str:
    """pg_dump/pg_restore/psql: NEXO_PG_BIN → PATH → PostgreSQL embutido (pgserver, instalação local)."""
    pastas = []
    if config()["PG_BIN"]:
        pastas.append(config()["PG_BIN"])
    pastas.append(None)  # PATH
    try:
        import pgserver

        pastas.append(str(Path(pgserver.__file__).parent / "pginstall" / "bin"))
    except ImportError:
        pass
    for pasta in pastas:
        achado = shutil.which(nome, path=pasta) if pasta else shutil.which(nome)
        if achado:
            return achado
    raise ErroCopia(
        f"Não encontrei o programa {nome} do PostgreSQL. No servidor Linux instale o pacote "
        "postgresql-client da mesma versão do banco, ou informe a pasta em NEXO_PG_BIN."
    )


def ambiente_pg() -> dict:
    """Credenciais por variáveis de ambiente (a senha nunca aparece na linha de comando)."""
    banco = connection.settings_dict  # o mesmo banco que o Django usa (nos testes, o banco de teste)
    env = {**os.environ, "PGCLIENTENCODING": "UTF8", "PGDATABASE": banco["NAME"]}
    for chave, var in (("HOST", "PGHOST"), ("PORT", "PGPORT"), ("USER", "PGUSER"), ("PASSWORD", "PGPASSWORD")):
        if banco.get(chave):
            env[var] = str(banco[chave])
    return env


def _executar(cmd: list[str], descricao: str) -> str:
    resultado = subprocess.run(
        cmd, env=ambiente_pg(), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if resultado.returncode != 0:
        raise ErroCopia(
            f"{descricao} falhou: {_detalhe_falha(cmd[0], resultado.returncode, resultado.stderr, resultado.stdout)}"
        )
    return resultado.stdout


def _detalhe_falha(programa: str, codigo: int, stderr: str, stdout: str = "") -> str:
    """Mensagem do programa ou, se ele não disse nada (ex.: não chegou a abrir no Windows), o código de saída."""
    texto = (stderr or "").strip() or (stdout or "").strip()
    if texto:
        return texto[-1500:]
    dica = ""
    if codigo & 0xFFFFFFFF == 0xC0000135:
        dica = " — uma DLL necessária não foi encontrada"
    elif codigo & 0xFFFFFFFF == 0xC0000005:
        dica = " — o programa encerrou com erro de acesso à memória"
    return f"o programa não informou o motivo (código de saída {codigo}, 0x{codigo & 0xFFFFFFFF:08X}{dica}; programa: {programa})"


def _consultar(sql: str, parametros=None) -> list[tuple]:
    with connection.cursor() as cursor:
        cursor.execute(sql, parametros or [])
        return cursor.fetchall()


def migracoes_aplicadas() -> dict[str, list[str]]:
    from django.db.migrations.recorder import MigrationRecorder

    saida: dict[str, list[str]] = {}
    for app, nome in MigrationRecorder(connection).migration_qs.values_list("app", "name").order_by("app", "name"):
        saida.setdefault(app, []).append(nome)
    return saida


def migracoes_conhecidas() -> set[tuple[str, str]]:
    from django.db.migrations.loader import MigrationLoader

    return set(MigrationLoader(None, ignore_no_migrations=True).disk_migrations)


def contagens() -> dict:
    from apps.auditoria.models import EventoAuditoria
    from apps.contas.models import Usuario
    from apps.documentos.models import Documento

    return {
        "documentos": Documento.objects.count(),
        "usuarios": Usuario.objects.count(),
        "eventos_auditoria": EventoAuditoria.objects.count(),
    }


# --------------------------------------------------------------------------
# Leitura e escrita com SHA-256
# --------------------------------------------------------------------------
class _LeitorComHash:
    def __init__(self, arquivo):
        self._arquivo = arquivo
        self.hash = hashlib.sha256()

    def read(self, n=-1):
        dados = self._arquivo.read(n)
        self.hash.update(dados)
        return dados


def sha256_arquivo(caminho: Path) -> str:
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(_BLOCO), b""):
            h.update(bloco)
    return h.hexdigest()


def _adicionar(tar: tarfile.TarFile, nome: str, caminho: Path) -> str:
    info = tar.gettarinfo(str(caminho), arcname=nome)
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    with open(caminho, "rb") as f:
        leitor = _LeitorComHash(f)
        tar.addfile(info, leitor)
    return leitor.hash.hexdigest()


# --------------------------------------------------------------------------
# Criar
# --------------------------------------------------------------------------
@dataclass
class ResultadoCopia:
    caminho: Path
    bytes: int
    sha256: str
    manifesto: dict


def criar(
    destino: Path | None = None, senha: str | None = None, rotulo: str = ROTULO_AGENDADA, sem_cifra: bool = False
) -> ResultadoCopia:
    """Gera o pacote. Sem senha, só com `sem_cifra=True` (ou NEXO_BACKUP_EXIGIR_SENHA=false)."""
    from apps.auditoria.servico import registrar

    senha = senha if senha is not None else config()["SENHA"]
    if not senha and config()["EXIGIR_SENHA"] and not sem_cifra:
        raise ErroCopia(
            "Defina NEXO_BACKUP_SENHA no .env para cifrar a cópia (os documentos são institucionais). "
            "Para uma cópia sem cifra, use --sem-cifra."
        )
    destino = Path(destino) if destino else pasta_copias()
    destino.mkdir(parents=True, exist_ok=True)
    carimbo = timezone.localtime().strftime("%Y%m%d-%H%M%S")
    final = destino / f"{rotulo}-{carimbo}{EXTENSAO}"
    parcial = final.with_name(final.name + ".parcial")
    armazenamento = Path(settings.NEXO_ARMAZENAMENTO_DIR)

    try:
        with tempfile.TemporaryDirectory(dir=destino, prefix=".copia-") as tmp:
            dump = Path(tmp) / "banco.dump"
            _executar([binario("pg_dump"), "-Fc", "--no-owner", "--no-privileges", "-f", str(dump)], "pg_dump")
            manifesto = {
                "formato": FORMATO,
                "criada_em": timezone.localtime().isoformat(),
                "cifrada": bool(senha),
                "postgres_servidor": _consultar("SHOW server_version")[0][0],
                "pg_dump": _executar([binario("pg_dump"), "--version"], "pg_dump --version").strip(),
                "extensoes": sorted(n for (n,) in _consultar("SELECT extname FROM pg_extension") if n != "plpgsql"),
                "migracoes": migracoes_aplicadas(),
                "contagens": contagens(),
            }
            with open(parcial, "wb") as bruto:
                saida = EscritorCifrado(bruto, senha) if senha else bruto
                with tarfile.open(fileobj=saida, mode="w|", format=tarfile.PAX_FORMAT) as tar:
                    manifesto["banco"] = {"sha256": _adicionar(tar, "banco.dump", dump), "bytes": dump.stat().st_size}
                    itens, total = {}, 0
                    if armazenamento.exists():
                        for caminho in sorted(
                            p for p in armazenamento.rglob("*") if p.is_file() and not p.is_symlink()
                        ):
                            relativo = caminho.relative_to(armazenamento).as_posix()
                            itens[relativo] = _adicionar(tar, f"arquivos/{relativo}", caminho)
                            total += caminho.stat().st_size
                    manifesto["arquivos"] = {"quantidade": len(itens), "bytes": total, "itens": itens}
                    dados = json.dumps(manifesto, ensure_ascii=False, indent=2).encode("utf-8")
                    info = tarfile.TarInfo("manifesto.json")
                    info.size = len(dados)
                    info.mtime = int(timezone.now().timestamp())
                    tar.addfile(info, _LeitorComHash(_BytesLeitura(dados)))
                if senha:
                    saida.close()
        parcial.replace(final)
    except (ErroCopia, ErroCifra, OSError) as erro:
        parcial.unlink(missing_ok=True)
        registrar(None, "COPIA_SEGURANCA", resultado="FALHA", detalhes={"rotulo": rotulo, "erro": str(erro)[:500]})
        if isinstance(erro, ErroCopia):
            raise
        raise ErroCopia(str(erro)) from erro

    resumo = {
        "arquivo": final.name,
        "criada_em": manifesto["criada_em"],
        "bytes": final.stat().st_size,
        "sha256": sha256_arquivo(final),
        "cifrada": manifesto["cifrada"],
        "rotulo": rotulo,
        "formato": FORMATO,
        "contagens": manifesto["contagens"],
        "arquivos": manifesto["arquivos"]["quantidade"],
    }
    _lateral(final).write_text(json.dumps(resumo, ensure_ascii=False, indent=2), encoding="utf-8")
    registrar(
        None,
        "COPIA_SEGURANCA",
        detalhes={k: resumo[k] for k in ("arquivo", "bytes", "sha256", "cifrada", "arquivos")},
    )
    if rotulo == ROTULO_AGENDADA and destino == pasta_copias():
        aplicar_retencao(destino, config()["RETENCAO"])
    return ResultadoCopia(final, resumo["bytes"], resumo["sha256"], manifesto)


class _BytesLeitura:
    def __init__(self, dados: bytes):
        self._dados, self._pos = dados, 0

    def read(self, n=-1):
        fim = len(self._dados) if n is None or n < 0 else self._pos + n
        trecho = self._dados[self._pos : fim]
        self._pos += len(trecho)
        return trecho


def _lateral(pacote: Path) -> Path:
    return pacote.with_name(pacote.name + ".json")


def aplicar_retencao(pasta: Path, manter: int) -> list[str]:
    """Mantém as `manter` cópias agendadas mais recentes. Cópias feitas antes de restaurar não entram."""
    if manter <= 0:
        return []
    agendadas = sorted(
        (p for p in pasta.iterdir() if _PADRAO_AGENDADA.match(p.name)), key=lambda p: p.name, reverse=True
    )
    removidas = []
    for antiga in agendadas[manter:]:
        antiga.unlink(missing_ok=True)
        _lateral(antiga).unlink(missing_ok=True)
        removidas.append(antiga.name)
    return removidas


def listar(pasta: Path | None = None) -> list[dict]:
    pasta = Path(pasta) if pasta else pasta_copias()
    saida = []
    for pacote in sorted(pasta.glob(f"*{EXTENSAO}"), key=lambda p: p.name, reverse=True):
        try:
            dados = json.loads(_lateral(pacote).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            dados = {"arquivo": pacote.name, "bytes": pacote.stat().st_size, "cifrada": esta_cifrado(pacote)}
        dados["caminho"] = str(pacote)
        saida.append(dados)
    return saida


# --------------------------------------------------------------------------
# Ler, verificar
# --------------------------------------------------------------------------
def _nome_seguro(nome: str) -> PurePosixPath:
    caminho = PurePosixPath(nome)
    if caminho.is_absolute() or ".." in caminho.parts or not caminho.parts or "\\" in nome:
        raise ErroCopia(f"Item suspeito no pacote: {nome!r}")
    return caminho


def abrir_pacote(caminho: Path, senha: str | None, extrair_em: Path | None = None) -> dict:
    """Lê o pacote inteiro, confere o SHA-256 de cada item com o manifesto e devolve o manifesto.

    Com `extrair_em`, grava `banco.dump` e `arquivos/` nessa pasta."""
    caminho = Path(caminho)
    if not caminho.exists():
        raise ErroCopia(f"Arquivo não encontrado: {caminho}")
    lateral = _lateral(caminho)
    if lateral.exists():
        esperado = json.loads(lateral.read_text(encoding="utf-8")).get("sha256")
        if esperado and sha256_arquivo(caminho) != esperado:
            raise ErroCopia("O pacote foi alterado ou está corrompido (SHA-256 diferente do registrado).")
    cifrado = esta_cifrado(caminho)
    senha = senha if senha is not None else config()["SENHA"]
    if cifrado and not senha:
        raise ErroCopia("Esta cópia é cifrada: informe a senha (NEXO_BACKUP_SENHA ou --senha).")

    hashes: dict[str, str] = {}
    manifesto = None
    with open(caminho, "rb") as bruto:
        try:
            entrada = LeitorCifrado(bruto, senha) if cifrado else bruto
            with tarfile.open(fileobj=entrada, mode="r|") as tar:
                for membro in tar:
                    nome = _nome_seguro(membro.name)
                    if membro.isdir():
                        continue
                    if not membro.isfile():
                        raise ErroCopia(f"Tipo de item não permitido no pacote: {membro.name}")
                    origem = tar.extractfile(membro)
                    if nome.as_posix() == "manifesto.json":
                        manifesto = json.loads(origem.read().decode("utf-8"))
                        continue
                    if nome.parts[0] not in ("banco.dump", "arquivos"):
                        raise ErroCopia(f"Item inesperado no pacote: {membro.name}")
                    h = hashlib.sha256()
                    destino = None
                    if extrair_em is not None:
                        alvo = Path(extrair_em, *nome.parts)
                        alvo.parent.mkdir(parents=True, exist_ok=True)
                        destino = open(alvo, "wb")
                    try:
                        while bloco := origem.read(_BLOCO):
                            h.update(bloco)
                            if destino:
                                destino.write(bloco)
                    finally:
                        if destino:
                            destino.close()
                    hashes[nome.as_posix()] = h.hexdigest()
        except ErroCifra as erro:
            raise ErroCopia(str(erro)) from erro
        except tarfile.TarError as erro:
            raise ErroCopia(f"Pacote ilegível: {erro}") from erro

    if manifesto is None:
        raise ErroCopia("Pacote sem manifesto (incompleto ou não é uma cópia do Nexo).")
    if manifesto.get("formato") != FORMATO:
        raise ErroCopia(f"Formato de cópia {manifesto.get('formato')} não suportado por esta versão do Nexo.")
    esperados = {"banco.dump": manifesto["banco"]["sha256"]}
    esperados.update({f"arquivos/{k}": v for k, v in manifesto["arquivos"]["itens"].items()})
    if hashes != esperados:
        diferentes = sorted(set(hashes) ^ set(esperados) | {k for k in hashes if hashes[k] != esperados.get(k)})
        raise ErroCopia(f"Conteúdo do pacote não confere com o manifesto: {', '.join(diferentes[:5])}")
    return manifesto


def verificar(caminho: Path, senha: str | None = None) -> dict:
    """Confere o pacote e se o PostgreSQL consegue ler o dump (sem tocar no banco)."""
    with tempfile.TemporaryDirectory(prefix="nexo-verificacao-") as tmp:
        manifesto = abrir_pacote(caminho, senha, extrair_em=Path(tmp))
        toc = _executar([binario("pg_restore"), "--list", str(Path(tmp) / "banco.dump")], "pg_restore --list")
    return {
        "arquivo": Path(caminho).name,
        "criada_em": manifesto["criada_em"],
        "cifrada": manifesto["cifrada"],
        "contagens": manifesto["contagens"],
        "arquivos": manifesto["arquivos"]["quantidade"],
        "objetos_no_banco": sum(1 for linha in toc.splitlines() if linha and not linha.startswith(";")),
        "compatibilidade": compatibilidade(manifesto),
    }


def compatibilidade(manifesto: dict) -> str:
    """ "igual", "anterior" (migrate completa depois) ou lança ErroCopia se a cópia for de versão mais nova."""
    conhecidas = migracoes_conhecidas()
    da_copia = {(app, nome) for app, nomes in manifesto["migracoes"].items() for nome in nomes}
    desconhecidas = sorted(f"{a}.{n}" for a, n in da_copia - conhecidas)
    if desconhecidas:
        raise ErroCopia(
            "A cópia é de uma versão mais nova do Nexo (migrações desconhecidas: "
            f"{', '.join(desconhecidas[:5])}). Atualize o Nexo antes de restaurar."
        )
    return "igual" if da_copia == conhecidas else "anterior"


# --------------------------------------------------------------------------
# Restaurar
# --------------------------------------------------------------------------
_LIMPAR_ESQUEMA = r"""
DO $$
DECLARE r record;
BEGIN
    -- Remove tudo o que é do Nexo no esquema public, preservando objetos de extensões (vector, unaccent).
    FOR r IN
        SELECT c.oid::regclass::text AS nome,
               CASE c.relkind WHEN 'v' THEN 'VIEW' WHEN 'm' THEN 'MATERIALIZED VIEW'
                              WHEN 'S' THEN 'SEQUENCE' WHEN 'f' THEN 'FOREIGN TABLE' ELSE 'TABLE' END AS tipo
        FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                          AND d.objid = c.oid AND d.deptype = 'e')
          AND NOT (c.relkind = 'S' AND EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_class'::regclass
                          AND d.objid = c.oid AND d.deptype IN ('a', 'i')))
    LOOP
        EXECUTE format('DROP %s IF EXISTS %s CASCADE', r.tipo, r.nome);
    END LOOP;
    FOR r IN
        SELECT p.oid::regprocedure::text AS nome FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE n.nspname = 'public' AND p.prokind IN ('f', 'p')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_proc'::regclass
                          AND d.objid = p.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP ROUTINE IF EXISTS %s CASCADE', r.nome);
    END LOOP;
    FOR r IN
        SELECT t.oid::regconfig::text AS nome FROM pg_ts_config t JOIN pg_namespace n ON n.oid = t.cfgnamespace
        WHERE n.nspname = 'public' AND NOT EXISTS (SELECT 1 FROM pg_depend d
              WHERE d.classid = 'pg_ts_config'::regclass AND d.objid = t.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP TEXT SEARCH CONFIGURATION IF EXISTS %s CASCADE', r.nome);
    END LOOP;
    FOR r IN
        SELECT t.oid::regdictionary::text AS nome FROM pg_ts_dict t JOIN pg_namespace n ON n.oid = t.dictnamespace
        WHERE n.nspname = 'public' AND NOT EXISTS (SELECT 1 FROM pg_depend d
              WHERE d.classid = 'pg_ts_dict'::regclass AND d.objid = t.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP TEXT SEARCH DICTIONARY IF EXISTS %s CASCADE', r.nome);
    END LOOP;
    FOR r IN
        SELECT t.oid::regtype::text AS nome FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
        WHERE n.nspname = 'public' AND t.typtype IN ('e', 'd')
          AND NOT EXISTS (SELECT 1 FROM pg_depend d WHERE d.classid = 'pg_type'::regclass
                          AND d.objid = t.oid AND d.deptype = 'e')
    LOOP
        EXECUTE format('DROP TYPE IF EXISTS %s CASCADE', r.nome);
    END LOOP;
END $$;
"""


def outras_conexoes() -> list[str]:
    linhas = _consultar(
        "SELECT coalesce(nullif(application_name, ''), 'sem nome') || ' (' || coalesce(client_addr::text, 'local') || ')' "
        "FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() "
        "AND backend_type = 'client backend'"
    )
    return [n for (n,) in linhas]


def _restaurar_banco(dump: Path, extensoes: list[str], tmp: Path):
    """Limpa o esquema e carrega o dump numa ÚNICA transação: se algo falhar, o banco fica como estava."""
    toc = _executar([binario("pg_restore"), "--list", str(dump)], "pg_restore --list")
    filtrada = [linha for linha in toc.splitlines() if not re.search(r"\b(EXTENSION|SCHEMA - public)\b", linha)]
    lista = tmp / "itens.lista"
    lista.write_text("\n".join(filtrada) + "\n", encoding="utf-8")
    prefixo = tmp / "prefixo.sql"
    criar_ext = "".join(f'CREATE EXTENSION IF NOT EXISTS "{e}";\n' for e in extensoes if re.fullmatch(r"[a-z0-9_]+", e))
    prefixo.write_text(criar_ext + _LIMPAR_ESQUEMA, encoding="utf-8")

    # 1) gera o SQL completo e confere que o pg_restore terminou bem (um canal direto para o psql poderia
    #    confirmar uma carga parcial se o pg_restore parasse no meio);
    sql = tmp / "restauracao.sql"
    _executar(
        [binario("pg_restore"), "--no-owner", "--no-privileges", "-L", str(lista), "-f", str(sql), str(dump)],
        "pg_restore (banco não alterado)",
    )
    # 2) limpa o esquema e carrega tudo numa única transação.
    connections.close_all()
    carga = subprocess.run(
        [
            binario("psql"),
            "-X",
            "-q",
            "-v",
            "ON_ERROR_STOP=1",
            "--single-transaction",
            "-f",
            str(prefixo),
            "-f",
            str(sql),
        ],
        capture_output=True,
        env=ambiente_pg(),
    )
    if carga.returncode != 0:
        detalhe = _detalhe_falha(
            "psql", carga.returncode, carga.stderr.decode("utf-8", "replace"), carga.stdout.decode("utf-8", "replace")
        )
        raise ErroCopia(f"A carga do banco falhou e foi desfeita: {detalhe}")


def _trocar_arquivos(novos: Path, manter_antigos: bool) -> Path | None:
    armazenamento = Path(settings.NEXO_ARMAZENAMENTO_DIR)
    novos.mkdir(parents=True, exist_ok=True)
    antigos = None
    if armazenamento.exists():
        antigos = armazenamento.with_name(f"{armazenamento.name}.substituido-{timezone.localtime():%Y%m%d-%H%M%S}")
        armazenamento.rename(antigos)
    shutil.move(str(novos), str(armazenamento))
    if antigos and not manter_antigos:
        shutil.rmtree(antigos, ignore_errors=True)
        return None
    return antigos


@dataclass
class ResultadoRestauracao:
    manifesto: dict
    copia_previa: Path | None
    arquivos_antigos: Path | None
    integridade_auditoria: dict


def restaurar(
    caminho: Path,
    senha: str | None = None,
    *,
    copia_previa: bool = True,
    forcar: bool = False,
    avisar=lambda texto: None,
) -> ResultadoRestauracao:
    from django.core.management import call_command

    from apps.auditoria.servico import registrar, verificar_integridade

    caminho = Path(caminho)
    armazenamento = Path(settings.NEXO_ARMAZENAMENTO_DIR)
    armazenamento.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=armazenamento.parent, prefix=".restauracao-") as tmp_texto:
        tmp = Path(tmp_texto)
        avisar("Conferindo o pacote...")
        manifesto = abrir_pacote(caminho, senha, extrair_em=tmp / "pacote")
        situacao = compatibilidade(manifesto)

        conexoes = outras_conexoes()
        if conexoes and not forcar:
            raise ErroCopia(
                "Pare o Nexo antes de restaurar (há conexões abertas no banco: "
                f"{', '.join(conexoes[:5])}). Use --forcar só se tiver certeza de que estão paradas."
            )

        previa = None
        if copia_previa:
            avisar("Fazendo cópia do estado atual antes de restaurar...")
            previa = criar(rotulo=ROTULO_ANTES_RESTAURACAO, senha=config()["SENHA"] or senha, sem_cifra=True).caminho

        avisar("Restaurando o banco...")
        _restaurar_banco(tmp / "pacote" / "banco.dump", manifesto.get("extensoes", []), tmp)

        avisar("Restaurando os arquivos...")
        antigos = _trocar_arquivos(tmp / "pacote" / "arquivos", manter_antigos=not copia_previa)

    if situacao == "anterior":
        avisar("Atualizando o banco para esta versão do Nexo (migrate)...")
        call_command("migrate", interactive=False, verbosity=0)

    integridade = verificar_integridade()
    registrar(
        None,
        "RESTAURACAO",
        detalhes={
            "arquivo": caminho.name,
            "copia_criada_em": manifesto["criada_em"],
            "copia_previa": previa.name if previa else None,
            "auditoria_integra_ao_restaurar": integridade["integra"],
        },
    )
    return ResultadoRestauracao(manifesto, previa, antigos, integridade)
