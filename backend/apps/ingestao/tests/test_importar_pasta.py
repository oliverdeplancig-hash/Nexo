"""Carga inicial do acervo a partir de uma pasta (ADR-025)."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.documentos.models import Documento, StatusDocumento

pytestmark = pytest.mark.django_db


@pytest.fixture
def importador(usuarios, perfis):
    usuarios["ti"].perfis.add(perfis["gestor"])
    return usuarios["ti"]


def test_importa_processa_e_pula_repetidos(tmp_path, importador, capsys):
    (tmp_path / "a.md").write_text("# Norma A\n\nConteúdo da norma A sobre diárias.", encoding="utf-8")
    (tmp_path / "b.txt").write_text("Procedimento B sobre férias.", encoding="utf-8")
    (tmp_path / "ignorar.exe").write_bytes(b"MZ")
    call_command("importar_pasta", str(tmp_path), usuario="ti", setor="TI", classificacao="geral")
    docs = Documento.objects.filter(setor_responsavel__sigla="TI", nome_arquivo_original__in=["a.md", "b.txt"])
    assert docs.count() == 2 and all(d.status == StatusDocumento.DISPONIVEL for d in docs)
    call_command("importar_pasta", str(tmp_path), usuario="ti", setor="TI")
    assert "já existentes: 2" in capsys.readouterr().out


def test_recusa_usuario_sem_funcao_e_setor_inexistente(tmp_path, usuarios, importador):
    with pytest.raises(CommandError, match="função de importar"):
        call_command("importar_pasta", str(tmp_path), usuario="gp", setor="TI")
    with pytest.raises(CommandError, match="Setor não encontrado"):
        call_command("importar_pasta", str(tmp_path), usuario="ti", setor="XYZ")
