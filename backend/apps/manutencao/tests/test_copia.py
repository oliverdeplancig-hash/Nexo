"""Cópia de segurança e restauração com o PostgreSQL real (pg_dump, pg_restore e psql)."""

import io
import json
import shutil
import tarfile

import psycopg
import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection

from apps.auditoria.models import EventoAuditoria
from apps.auditoria.servico import verificar_integridade
from apps.contas.models import Usuario
from apps.documentos.models import Documento
from apps.manutencao import copia
from apps.manutencao.cifra import TAMANHO_BLOCO, ErroCifra, EscritorCifrado, LeitorCifrado

SENHA = "senha-de-teste-forte"


@pytest.fixture(autouse=True)
def _pasta_de_copias_isolada():
    shutil.rmtree(settings.NEXO_BACKUP["DIR"], ignore_errors=True)
    yield
    shutil.rmtree(settings.NEXO_BACKUP["DIR"], ignore_errors=True)


# ---------------------------------------------------------------- cifra
def _cifrar(dados: bytes, senha=SENHA) -> bytes:
    destino = io.BytesIO()
    escritor = EscritorCifrado(destino, senha)
    escritor.write(dados)
    escritor.close()
    return destino.getvalue()


def _decifrar(cifrado: bytes, senha=SENHA) -> bytes:
    return LeitorCifrado(io.BytesIO(cifrado), senha).read()


@pytest.mark.parametrize("tamanho", [0, 10, TAMANHO_BLOCO, TAMANHO_BLOCO * 2 + 7])
def test_cifra_ida_e_volta(tamanho):
    dados = bytes(range(256)) * (tamanho // 256) + b"x" * (tamanho % 256)
    cifrado = _cifrar(dados)
    assert dados[:64] not in cifrado or tamanho == 0
    assert _decifrar(cifrado) == dados


def test_cifra_recusa_senha_errada_corte_e_alteracao():
    cifrado = _cifrar(b"a" * (TAMANHO_BLOCO + 100))
    with pytest.raises(ErroCifra, match="Senha incorreta"):
        _decifrar(cifrado, "outra")
    with pytest.raises(ErroCifra, match="cortado"):
        _decifrar(cifrado[: len(cifrado) // 2])
    # cortar exatamente no fim do primeiro bloco também é detectado (falta o bloco final)
    primeiro = 32 + 4 + TAMANHO_BLOCO + 16
    with pytest.raises(ErroCifra, match="cortado"):
        _decifrar(cifrado[:primeiro])
    alterado = bytearray(cifrado)
    alterado[-5] ^= 1
    with pytest.raises(ErroCifra, match="corrompida"):
        _decifrar(bytes(alterado))


# ---------------------------------------------------------------- criar / verificar
@pytest.fixture
def acervo(transactional_db, usuarios, criar_documento):
    doc = criar_documento("Norma de plantão", "O plantão de fim de semana começa às 07h de sábado.")
    return {"doc": doc, "usuarios": usuarios}


def test_cria_cifrada_e_verifica(acervo):
    r = copia.criar(senha=SENHA)
    assert r.caminho.name.startswith("nexo-") and r.caminho.suffix == ".nexobak"
    assert r.caminho.read_bytes()[:8] == b"NEXOBK1\x00"
    assert b"plant" not in r.caminho.read_bytes()
    assert r.manifesto["contagens"]["documentos"] == 1
    assert r.manifesto["arquivos"]["quantidade"] == 1
    assert "vector" in r.manifesto["extensoes"]

    relatorio = copia.verificar(r.caminho, SENHA)
    assert relatorio["compatibilidade"] == "igual"
    assert relatorio["objetos_no_banco"] > 50
    with pytest.raises(copia.ErroCopia, match="cifrada"):
        copia.verificar(r.caminho, "")
    assert EventoAuditoria.objects.filter(tipo="COPIA_SEGURANCA", resultado="SUCESSO").exists()


def test_exige_senha_quando_configurado(acervo, settings):
    settings.NEXO_BACKUP = {**settings.NEXO_BACKUP, "EXIGIR_SENHA": True}
    with pytest.raises(copia.ErroCopia, match="NEXO_BACKUP_SENHA"):
        copia.criar()
    assert copia.criar(sem_cifra=True).manifesto["cifrada"] is False


def test_pacote_alterado_e_recusado(acervo):
    r = copia.criar()
    dados = bytearray(r.caminho.read_bytes())
    dados[len(dados) // 2] ^= 1
    r.caminho.write_bytes(bytes(dados))
    with pytest.raises(copia.ErroCopia, match="alterado ou está corrompido"):
        copia.verificar(r.caminho)
    # sem o arquivo lateral, o manifesto interno ainda pega a alteração
    copia._lateral(r.caminho).unlink()
    with pytest.raises(copia.ErroCopia):
        copia.verificar(r.caminho)


def test_pacote_com_caminho_malicioso_e_recusado(tmp_path, db):
    pacote = tmp_path / "malicioso.nexobak"
    with tarfile.open(pacote, "w") as tar:
        info = tarfile.TarInfo("../../fora.txt")
        info.size = 2
        tar.addfile(info, io.BytesIO(b"oi"))
    with pytest.raises(copia.ErroCopia, match="suspeito"):
        copia.abrir_pacote(pacote, None, extrair_em=tmp_path / "x")
    assert not (tmp_path.parent / "fora.txt").exists()


def test_copia_de_versao_mais_nova_e_recusada(db):
    manifesto = {"migracoes": {"contas": ["0001_initial", "9999_do_futuro"]}}
    with pytest.raises(copia.ErroCopia, match="mais nova"):
        copia.compatibilidade(manifesto)
    assert copia.compatibilidade({"migracoes": {"contas": ["0001_initial"]}}) == "anterior"


def test_retencao_mantem_as_mais_recentes(tmp_path):
    for i in range(5):
        (tmp_path / f"nexo-2026010{i}-120000.nexobak").write_bytes(b"x")
        (tmp_path / f"nexo-2026010{i}-120000.nexobak.json").write_text("{}")
    (tmp_path / "nexo-antes-restauracao-20250101-000000.nexobak").write_bytes(b"x")
    removidas = copia.aplicar_retencao(tmp_path, 2)
    assert removidas == ["nexo-20260102-120000.nexobak", "nexo-20260101-120000.nexobak", "nexo-20260100-120000.nexobak"]
    restantes = sorted(p.name for p in tmp_path.glob("*.nexobak"))
    assert restantes == [
        "nexo-20260103-120000.nexobak",
        "nexo-20260104-120000.nexobak",
        "nexo-antes-restauracao-20250101-000000.nexobak",
    ]
    assert not (tmp_path / "nexo-20260100-120000.nexobak.json").exists()


# ---------------------------------------------------------------- restaurar
def test_restauracao_completa_volta_banco_e_arquivos(acervo, cliente):
    doc = acervo["doc"]
    arquivo_doc = settings.NEXO_ARMAZENAMENTO_DIR / doc.arquivo.name
    original = arquivo_doc.read_bytes()
    r = copia.criar(senha=SENHA)

    # estrago depois da cópia: banco e arquivos
    Usuario.objects.create_user(username="criado-depois")
    Documento.objects.filter(pk=doc.pk).update(titulo="Título adulterado")
    arquivo_doc.write_bytes(b"conteudo trocado")
    (settings.NEXO_ARMAZENAMENTO_DIR / "lixo.txt").write_text("x")

    resultado = copia.restaurar(r.caminho, SENHA, avisar=print)

    assert not Usuario.objects.filter(username="criado-depois").exists()
    assert Documento.objects.get(pk=doc.pk).titulo == "Norma de plantão"
    assert arquivo_doc.read_bytes() == original
    assert not (settings.NEXO_ARMAZENAMENTO_DIR / "lixo.txt").exists()
    # cópia do estado anterior foi feita e contém o estrago
    assert resultado.copia_previa and resultado.copia_previa.name.startswith("nexo-antes-restauracao-")
    # auditoria: cadeia íntegra e restauração registrada por último
    assert verificar_integridade()["integra"]
    ultimo = EventoAuditoria.objects.order_by("-id").first()
    assert ultimo.tipo == "RESTAURACAO" and ultimo.detalhes["arquivo"] == r.caminho.name
    # busca (FTS nexo_pt + vetores) continua funcionando depois da restauração
    busca = cliente(acervo["usuarios"]["gp"]).get("/api/v1/busca/?q=plantao%20sabado").json()
    assert busca["resultados"][0]["documento"]["titulo"] == "Norma de plantão"
    # a trilha de auditoria continua somente-inserção depois da restauração
    with pytest.raises(Exception, match="somente-inserção"):
        with connection.cursor() as c:
            c.execute("DELETE FROM auditoria_eventoauditoria")


def test_restaurar_a_copia_previa_desfaz_a_restauracao(acervo):
    r = copia.criar()
    Usuario.objects.create_user(username="depois")
    resultado = copia.restaurar(r.caminho)
    assert not Usuario.objects.filter(username="depois").exists()
    copia.restaurar(resultado.copia_previa)
    assert Usuario.objects.filter(username="depois").exists()


def test_recusa_restaurar_com_o_nexo_em_uso(acervo):
    r = copia.criar()
    banco = connection.settings_dict
    outra = psycopg.connect(
        dbname=banco["NAME"],
        user=banco["USER"],
        password=banco["PASSWORD"],
        host=banco["HOST"],
        port=banco["PORT"],
        application_name="daphne",
    )
    try:
        with pytest.raises(copia.ErroCopia, match="Pare o Nexo"):
            copia.restaurar(r.caminho)
    finally:
        outra.close()
    assert Usuario.objects.count() == len(acervo["usuarios"])


def test_falha_na_carga_nao_altera_o_banco(acervo, monkeypatch):
    r = copia.criar()
    Usuario.objects.create_user(username="deve-continuar")
    # simula um dump que quebra no meio da carga
    original = copia._LIMPAR_ESQUEMA
    monkeypatch.setattr(copia, "_LIMPAR_ESQUEMA", original + "\nSELECT 1/0;\n")
    with pytest.raises(copia.ErroCopia, match="desfeita"):
        copia.restaurar(r.caminho, copia_previa=False)
    assert Usuario.objects.filter(username="deve-continuar").exists()


def test_comando_exige_confirmacao(acervo):
    r = copia.criar()
    with pytest.raises(CommandError, match="--confirmar"):
        call_command("copia_seguranca", "restaurar", str(r.caminho))
    call_command("copia_seguranca", "verificar", str(r.caminho))
    call_command("copia_seguranca", "listar")


def test_lateral_nao_expoe_conteudo(acervo):
    r = copia.criar(senha=SENHA)
    lateral = json.loads(copia._lateral(r.caminho).read_text())
    assert set(lateral) == {
        "arquivo",
        "criada_em",
        "bytes",
        "sha256",
        "cifrada",
        "rotulo",
        "formato",
        "contagens",
        "arquivos",
    }


def test_painel_de_copias_so_para_admin_de_permissoes(acervo, cliente, perfis):
    copia.criar()
    assert cliente(acervo["usuarios"]["gp"]).get("/api/v1/manutencao/copias/").status_code == 403
    adm = acervo["usuarios"]["admin"]
    adm.perfis.add(perfis["adminperm"])
    dados = cliente(adm).get("/api/v1/manutencao/copias/").json()
    assert dados["em_dia"] is True and len(dados["copias"]) == 1
    assert "caminho" not in dados["copias"][0]
