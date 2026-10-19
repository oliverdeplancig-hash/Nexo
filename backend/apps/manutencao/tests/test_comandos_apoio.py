"""Comandos de apoio: dados de demonstração, processador da fila e teste de carga (partes sem rede)."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.contas.models import Usuario
from apps.documentos.models import Documento, StatusDocumento

pytestmark = pytest.mark.django_db


def test_carregar_demo_so_com_depuracao(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError, match="NEXO_DEBUG"):
        call_command("carregar_demo")
    settings.DEBUG = True
    call_command("carregar_demo")
    assert Usuario.objects.filter(username__endswith=".demo").count() == 3
    assert Documento.objects.filter(status=StatusDocumento.DISPONIVEL).count() >= 4
    call_command("carregar_demo")  # repetir não duplica
    assert Usuario.objects.filter(username__endswith=".demo").count() == 3


@pytest.mark.django_db(transaction=True)  # o processador fecha conexões antigas a cada volta
def test_processar_fila_uma_vez(criar_documento):
    doc = criar_documento("Na fila", "Texto para processar depois.", processar_agora=False)
    assert doc.status == StatusDocumento.RECEBIDO
    call_command("processar_fila")
    doc.refresh_from_db()
    assert doc.status == StatusDocumento.DISPONIVEL


def test_teste_carga_valida_argumentos_e_resume(capsys):
    from apps.manutencao.management.commands.teste_carga import Command, Resultado, _percentil

    assert _percentil([], 95) == 0.0
    assert _percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 95) == 10
    with pytest.raises(CommandError, match="positivos"):
        call_command("teste_carga", url="http://x", usuario="a", senha="b", pessoas=0)
    r = Resultado(perguntas=3, respondidas=2, tempos=[1.0, 3.0], primeiro_retorno=[0.5, 1.0], ia_ocupada=1)
    r.origens.update({"rag": 1, "extrativo": 1})
    r.tempos_por_origem = {"rag": [3.0], "extrativo": [1.0]}
    comando = Command()
    comando._relatorio(r, 120, {"pessoas": 10})
    saida = capsys.readouterr().out
    assert "respondidas: 2" in saida and "só com trechos por fila cheia: 1" in saida
