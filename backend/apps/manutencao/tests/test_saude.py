"""Saúde do sistema (ADR-023)."""

from collections import namedtuple
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.manutencao import saude
from apps.manutencao.models import SinalDeVida
from apps.notificacoes.models import Notificacao

pytestmark = pytest.mark.django_db


@pytest.fixture
def administrador(usuarios, perfis):
    usuarios["admin"].perfis.add(perfis["adminperm"])
    return usuarios["admin"]


def test_painel_so_para_quem_administra_permissoes(cliente, usuarios, administrador):
    assert cliente(usuarios["gp"]).get("/api/v1/manutencao/saude/").status_code == 403
    r = cliente(administrador).get("/api/v1/manutencao/saude/")
    assert r.status_code == 200
    codigos = {i["codigo"] for i in r.json()["itens"]}
    assert {"configuracao", "banco", "disco", "copias", "processamento", "ia"} <= codigos
    assert r.json()["versao"]


def test_processador_da_fila_sem_sinal_e_com_sinal(settings):
    settings.NEXO_INGESTAO = {**settings.NEXO_INGESTAO, "PROCESSAR_IMEDIATAMENTE": False}
    assert saude.verificar_processamento().situacao == saude.ATENCAO
    saude._ultimo_sinal.clear()
    saude.sinal_de_vida(saude.PROCESSO_FILA)
    assert saude.verificar_processamento().situacao == saude.OK
    SinalDeVida.objects.update(atualizado_em=timezone.now() - timedelta(minutes=10))
    assert "sem sinal" in saude.verificar_processamento().resumo


def test_disco_quase_cheio(monkeypatch):
    Uso = namedtuple("Uso", "total used free")
    monkeypatch.setattr(saude.shutil, "disk_usage", lambda _: Uso(100, 97, 3))
    v = saude.verificar_disco()
    assert v.situacao == saude.PROBLEMA and "Documentos e cópias" in v.resumo


def test_certificado_vencendo(tmp_path):
    call_command("gerar_certificado", pasta=str(tmp_path), dias=10)
    v = saude.verificar_certificado(tmp_path)
    assert v.situacao == saude.ATENCAO and v.detalhes["autoassinado"]
    assert saude.verificar_certificado(tmp_path / "nao-existe") is None


def test_ia_de_teste_e_configuracao(settings):
    settings.NEXO_IA = {**settings.NEXO_IA, "PROVEDOR": "falso"}
    assert saude.verificar_ia().situacao == saude.ATENCAO
    settings.DEBUG = True
    assert saude.verificar_configuracao().situacao == saude.PROBLEMA


def test_avisa_administradores_uma_vez_por_dia(usuarios, administrador, settings, tmp_path):
    settings.NEXO_BACKUP = {**settings.NEXO_BACKUP, "DIR": tmp_path}  # nenhuma cópia → problema
    assert saude.avisar() >= 1
    avisos = Notificacao.objects.filter(usuario=administrador, tipo="saude_sistema")
    assert avisos.filter(dados__codigo="copias").count() == 1
    assert not Notificacao.objects.filter(usuario=usuarios["gp"], tipo="saude_sistema").exists()
    saude.avisar()
    assert avisos.filter(dados__codigo="copias").count() == 1  # não repete no mesmo dia


def test_comando_sai_com_erro_quando_ha_problema(settings, tmp_path, capsys):
    settings.NEXO_BACKUP = {**settings.NEXO_BACKUP, "DIR": tmp_path}
    with pytest.raises(SystemExit):
        call_command("verificar_saude")
    assert "Cópias de segurança" in capsys.readouterr().out
