"""Coleções: criar, editar, excluir e organizar documentos, sem alterar permissões."""

import pytest

from apps.acesso.models import Classificacao
from apps.documentos.models import Colecao, Documento


@pytest.fixture
def docs(criar_documento):
    return {
        "geral": criar_documento("Manual de férias", "Texto sobre férias.", processar_agora=False),
        "restrito_ti": criar_documento(
            "Plano de contingência",
            "Texto restrito.",
            setor="TI",
            classificacao=Classificacao.RESTRITO,
            processar_agora=False,
        ),
    }


def _disponibilizar(*documentos):
    Documento.objects.filter(pk__in=[d.pk for d in documentos]).update(status="disponivel")


def test_servidor_gerencia_a_propria_colecao_pessoal(cliente, usuarios, docs):
    _disponibilizar(*docs.values())
    c = cliente(usuarios["gp"])
    r = c.post("/api/v1/colecoes/", {"nome": "  Minhas leituras ", "pessoal": True}, format="json")
    assert r.status_code == 201, r.content
    col = r.json()
    assert col["nome"] == "Minhas leituras" and col["pode_editar"] is True

    r = c.post(
        f"/api/v1/colecoes/{col['id']}/documentos/",
        {"documentos": [docs["geral"].id, docs["restrito_ti"].id]},
        format="json",
    )
    assert r.json() == {"adicionados": 1, "ignorados": 1}  # o restrito de TI não é visível para GP
    lista = c.get(f"/api/v1/documentos/?colecao={col['id']}").json()["results"]
    assert [d["titulo"] for d in lista] == ["Manual de férias"]

    assert (
        c.patch(f"/api/v1/colecoes/{col['id']}/", {"nome": "Leituras", "pessoal": False}, format="json").status_code
        == 200
    )
    colecao = Colecao.objects.get(pk=col["id"])
    assert colecao.nome == "Leituras" and colecao.pessoal is True  # pessoal não muda depois de criada

    assert c.delete(f"/api/v1/colecoes/{col['id']}/documentos/{docs['geral'].id}/").status_code == 204
    assert not colecao.documentos.exists()
    assert c.delete(f"/api/v1/colecoes/{col['id']}/").status_code == 204
    assert not Colecao.objects.filter(pk=col["id"]).exists()
    assert Documento.objects.filter(pk=docs["geral"].pk).exists()  # excluir coleção não apaga documentos


def test_colecao_pessoal_e_invisivel_e_intocavel_para_outros(cliente, usuarios, docs):
    _disponibilizar(*docs.values())
    dono = cliente(usuarios["gp"])
    col = dono.post("/api/v1/colecoes/", {"nome": "Particular", "pessoal": True}, format="json").json()
    dono.post(f"/api/v1/colecoes/{col['id']}/documentos/", {"documentos": [docs["geral"].id]}, format="json")

    outro = cliente(usuarios["gestor"])  # tem gerir_colecoes, mas a coleção é pessoal de outra pessoa
    assert col["id"] not in [x["id"] for x in outro.get("/api/v1/colecoes/").json()["results"]]
    assert outro.patch(f"/api/v1/colecoes/{col['id']}/", {"nome": "x"}, format="json").status_code == 404
    assert outro.delete(f"/api/v1/colecoes/{col['id']}/").status_code == 404
    assert outro.get(f"/api/v1/documentos/?colecao={col['id']}").json()["results"] == []
    detalhe = outro.get(f"/api/v1/documentos/{docs['geral'].id}/").json()
    assert detalhe["colecoes"] == []  # o nome da coleção pessoal alheia não vaza


def test_colecao_institucional_exige_gerir_colecoes(cliente, usuarios, docs):
    _disponibilizar(*docs.values())
    from apps.contas.models import Perfil, Usuario

    organizador = Perfil.objects.create(codigo="organizador", nome="Organizador", funcoes=["gerir_colecoes"])
    usuarios["gestor"].perfis.add(organizador)
    gestor = cliente(Usuario.objects.get(pk=usuarios["gestor"].pk))
    r = gestor.post("/api/v1/colecoes/", {"nome": "Normas de pessoal", "pessoal": False}, format="json")
    assert r.status_code == 201, r.content
    col = r.json()

    servidor = cliente(usuarios["gp"])
    assert servidor.post("/api/v1/colecoes/", {"nome": "Inst", "pessoal": False}, format="json").status_code == 403
    vista = next(x for x in servidor.get("/api/v1/colecoes/").json()["results"] if x["id"] == col["id"])
    assert vista["pode_editar"] is False
    assert servidor.patch(f"/api/v1/colecoes/{col['id']}/", {"nome": "x"}, format="json").status_code == 403
    assert (
        servidor.post(
            f"/api/v1/colecoes/{col['id']}/documentos/", {"documentos": [docs["geral"].id]}, format="json"
        ).status_code
        == 403
    )
    assert servidor.delete(f"/api/v1/colecoes/{col['id']}/").status_code == 403
    assert gestor.delete(f"/api/v1/colecoes/{col['id']}/").status_code == 204


def test_nome_vazio_e_ciclo_sao_recusados(cliente, usuarios):
    c = cliente(usuarios["gp"])
    assert c.post("/api/v1/colecoes/", {"nome": "  ", "pessoal": True}, format="json").status_code == 400
    a = c.post("/api/v1/colecoes/", {"nome": "A", "pessoal": True}, format="json").json()
    b = c.post("/api/v1/colecoes/", {"nome": "B", "pessoal": True, "superior": a["id"]}, format="json").json()
    r = c.patch(f"/api/v1/colecoes/{a['id']}/", {"superior": b["id"]}, format="json")
    assert r.status_code == 400 and "dentro dela mesma" in r.content.decode()
