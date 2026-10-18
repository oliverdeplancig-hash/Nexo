import hashlib
import shutil

import pytest
from django.conf import settings
from django.core.files.base import ContentFile

from apps.acesso.models import Classificacao
from apps.contas.models import Funcao, Perfil, Usuario
from apps.documentos.models import Documento
from apps.ingestao.pipeline import processar
from apps.organizacao.models import Setor


@pytest.fixture(autouse=True)
def _armazenamento_isolado():
    yield
    shutil.rmtree(settings.NEXO_ARMAZENAMENTO_DIR, ignore_errors=True)


@pytest.fixture
def setores(db):
    return {
        "GP": Setor.objects.create(
            sigla="GP",
            nome="Gestão de Pessoas",
            competencias="férias licenças frequência",
            palavras_chave=["férias", "licença"],
        ),
        "TI": Setor.objects.create(
            sigla="TI",
            nome="Tecnologia da Informação",
            competencias="senha rede sistemas",
            palavras_chave=["senha", "rede"],
            canal_contato="canal-ti",
            contato_visivel_para_todos=False,
        ),
    }


@pytest.fixture
def perfis(db):
    return {
        "servidor": Perfil.objects.create(codigo="servidor", nome="Servidor", funcoes=[]),
        "gestor": Perfil.objects.create(
            codigo="gestor", nome="Gestor", funcoes=[Funcao.IMPORTAR_DOCUMENTOS, Funcao.GERIR_REGRAS]
        ),
        "auditor": Perfil.objects.create(codigo="auditor", nome="Auditor", funcoes=[Funcao.VER_AUDITORIA]),
        "admin": Perfil.objects.create(codigo="admin", nome="Admin", funcoes=[Funcao.ADMIN_USUARIOS]),
        "adminperm": Perfil.objects.create(
            codigo="adminperm", nome="Admin perm", funcoes=[Funcao.ADMIN_PERMISSOES, Funcao.ADMIN_USUARIOS]
        ),
    }


def _usuario(login, setor, *lista_perfis, **extra):
    u = Usuario.objects.create_user(username=login, password="Senha-forte-123", setor=setor, **extra)
    u.perfis.set(lista_perfis)
    return u


@pytest.fixture
def usuarios(setores, perfis):
    return {
        "gp": _usuario("gp", setores["GP"], perfis["servidor"]),
        "ti": _usuario("ti", setores["TI"], perfis["servidor"]),
        "gestor": _usuario("gestor", setores["TI"], perfis["gestor"]),
        "auditor": _usuario("auditor", setores["GP"], perfis["auditor"]),
        "admin": _usuario("admin", setores["GP"], perfis["admin"]),
        "super": _usuario("super", None, is_superuser=True, is_staff=True),
    }


@pytest.fixture
def criar_documento(setores, usuarios):
    def _criar(
        titulo, conteudo, setor="GP", classificacao=Classificacao.GERAL, responsavel=None, processar_agora=True, **extra
    ):
        dados = conteudo.encode()
        doc = Documento(
            titulo=titulo,
            setor_responsavel=setores[setor],
            responsavel=responsavel,
            criado_por=responsavel,
            classificacao=classificacao,
            nome_arquivo_original=f"{titulo}.md",
            tipo_arquivo="md",
            tamanho_bytes=len(dados),
            hash_sha256=hashlib.sha256(dados).hexdigest(),
            **extra,
        )
        doc.arquivo.save(f"{titulo}.md", ContentFile(dados), save=False)
        doc.save()
        if processar_agora:
            processar(doc)
            doc.refresh_from_db()
        return doc

    return _criar


@pytest.fixture
def cliente():
    from rest_framework.test import APIClient

    def _cliente(usuario=None):
        c = APIClient()
        if usuario:
            c.force_authenticate(usuario)
        return c

    return _cliente
