from datetime import timedelta

import pytest
from django.utils import timezone

from apps.acesso.models import Acao, AutorizacaoDocumento, Classificacao
from apps.acesso.servico import decidir, documentos_visiveis
from apps.documentos.models import Documento, StatusDocumento

pytestmark = pytest.mark.django_db


def _ids(usuario, acao=Acao.CONSULTAR):
    return set(documentos_visiveis(usuario, acao).values_list("id", flat=True))


def test_geral_visivel_para_todos_mas_download_controlado(usuarios, criar_documento):
    doc = criar_documento("Geral", "conteúdo geral", classificacao=Classificacao.GERAL)
    assert doc.id in _ids(usuarios["ti"])
    assert not decidir(usuarios["ti"], doc).permite(Acao.BAIXAR)
    doc.permite_download_geral = True
    doc.save()
    assert decidir(usuarios["ti"], doc).permite(Acao.BAIXAR)


def test_setor_so_para_membros(usuarios, criar_documento):
    doc = criar_documento("Do GP", "conteúdo do setor", classificacao=Classificacao.SETOR, setor="GP")
    assert doc.id in _ids(usuarios["gp"])
    assert doc.id not in _ids(usuarios["ti"])
    assert decidir(usuarios["gp"], doc).permite(Acao.BAIXAR)
    assert not decidir(usuarios["gp"], doc).permite(Acao.EDITAR)


def test_superusuario_nao_tem_acesso_documental_automatico(usuarios, criar_documento):
    doc = criar_documento("Restrito", "segredo", classificacao=Classificacao.RESTRITO, setor="TI")
    assert doc.id not in _ids(usuarios["super"])
    assert decidir(usuarios["super"], doc).acoes == set()


def test_autorizacao_explicita_e_validade(usuarios, criar_documento):
    doc = criar_documento("Restrito", "segredo", classificacao=Classificacao.RESTRITO, setor="TI")
    aut = AutorizacaoDocumento.objects.create(documento=doc, usuario=usuarios["gp"], acoes=[Acao.VISUALIZAR])
    assert doc.id in _ids(usuarios["gp"], Acao.VISUALIZAR)
    assert doc.id not in _ids(usuarios["gp"], Acao.BAIXAR)
    aut.valido_ate = timezone.now() - timedelta(minutes=1)
    aut.save()
    assert doc.id not in _ids(usuarios["gp"])


def test_autorizacao_por_perfil_e_setor(usuarios, perfis, setores, criar_documento):
    doc = criar_documento("Restrito", "segredo", classificacao=Classificacao.RESTRITO, setor="TI")
    AutorizacaoDocumento.objects.create(documento=doc, perfil=perfis["auditor"], acoes=[Acao.CONSULTAR])
    assert doc.id in _ids(usuarios["auditor"])
    assert doc.id not in _ids(usuarios["auditor"], Acao.VISUALIZAR)
    AutorizacaoDocumento.objects.create(documento=doc, setor=setores["GP"], acoes=[Acao.BAIXAR])
    assert doc.id in _ids(usuarios["gp"], Acao.VISUALIZAR)


def test_documento_nao_disponivel_fica_oculto(usuarios, criar_documento):
    doc = criar_documento("Em processamento", "x" * 50, processar_agora=False, responsavel=usuarios["gestor"])
    assert doc.status == StatusDocumento.RECEBIDO
    assert doc.id not in _ids(usuarios["gp"])
    assert doc.id in _ids(usuarios["gestor"])  # o responsável acompanha o próprio cadastro


@pytest.mark.parametrize("acao", list(Acao.values))
def test_filtro_de_banco_equivale_a_decisao_individual(usuarios, perfis, setores, criar_documento, acao):
    """Propriedade central: documentos_visiveis(u, a) == {d | decidir(u, d).permite(a)}."""
    docs = [
        criar_documento("g", "texto geral um", classificacao=Classificacao.GERAL),
        criar_documento("g2", "texto geral dois", classificacao=Classificacao.GERAL, permite_download_geral=True),
        criar_documento("s", "texto setor", classificacao=Classificacao.SETOR, setor="TI"),
        criar_documento(
            "r", "texto restrito", classificacao=Classificacao.RESTRITO, setor="TI", responsavel=usuarios["ti"]
        ),
        criar_documento("p", "pendente", processar_agora=False),
    ]
    AutorizacaoDocumento.objects.create(documento=docs[3], perfil=perfis["auditor"], acoes=[Acao.EDITAR])
    AutorizacaoDocumento.objects.create(documento=docs[4], usuario=usuarios["admin"], acoes=[Acao.ADMINISTRAR])
    for usuario in usuarios.values():
        esperado = {d.id for d in Documento.objects.all() if decidir(usuario, d).permite(acao)}
        assert _ids(usuario, acao) == esperado, (usuario.username, acao)
