"""Login institucional pela conta Microsoft (ADR-010), com a Microsoft simulada."""

import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from apps.auditoria.models import EventoAuditoria
from apps.contas import entra
from apps.contas.models import Usuario

TENANT = "11111111-2222-3333-4444-555555555555"
CLIENTE = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
EMISSOR = f"https://login.microsoftonline.com/{TENANT}/v2.0"
META = {
    "authorization_endpoint": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/authorize",
    "token_endpoint": f"https://login.microsoftonline.com/{TENANT}/oauth2/v2.0/token",
    "jwks_uri": f"https://login.microsoftonline.com/{TENANT}/discovery/v2.0/keys",
    "issuer": EMISSOR,
}


def _chave():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


CHAVE = _chave()


def _jwks(chave):
    publica = RSAAlgorithm.to_jwk(chave.public_key(), as_dict=True)
    return {"keys": [{**publica, "kid": "k1", "use": "sig", "alg": "RS256"}]}


class MicrosoftFalsa:
    def __init__(self, monkeypatch):
        self.claims = {}
        self.chave_assinatura = CHAVE
        self.trocas = []
        monkeypatch.setattr(entra, "_get_json", self._get_json)
        monkeypatch.setattr(entra, "_post_form", self._post_form)

    def _get_json(self, url):
        if url.endswith("openid-configuration"):
            return META
        if url == META["jwks_uri"]:
            return _jwks(CHAVE)
        raise AssertionError(url)

    def _post_form(self, url, dados):
        self.trocas.append(dados)
        agora = int(time.time())
        claims = {
            "iss": EMISSOR,
            "aud": CLIENTE,
            "sub": "sub-1",
            "iat": agora,
            "nbf": agora,
            "exp": agora + 3600,
            "tid": TENANT,
            "oid": "oid-0001",
            "preferred_username": "Fulano.Tal@PM.BA.GOV.BR",
            "name": "Fulano de Tal",
            "nonce": self.nonce,
            **self.claims,
        }
        token = jwt.encode(claims, self.chave_assinatura, algorithm="RS256", headers={"kid": "k1"})
        return {"id_token": token, "token_type": "Bearer"}


@pytest.fixture(autouse=True)
def _sem_limite_de_tentativas():
    # O limite de 10 tentativas/min por IP é compartilhado entre os testes (cache em memória).
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def configurado(settings):
    settings.NEXO_ENTRA = {
        **settings.NEXO_ENTRA,
        "TENANT_ID": TENANT,
        "CLIENT_ID": CLIENTE,
        "CLIENT_SECRET": "segredo-de-teste",
        "REDIRECT_URI": "",
        "DOMINIOS": ["pm.ba.gov.br"],
        "CRIAR_USUARIOS": True,
        "PERFIL_PADRAO": "servidor",
    }
    entra.limpar_cache()
    yield settings
    entra.limpar_cache()


@pytest.fixture
def microsoft(monkeypatch, configurado):
    return MicrosoftFalsa(monkeypatch)


def _iniciar(client, microsoft, destino=None):
    url = "/api/v1/auth/microsoft/" + (f"?destino={destino}" if destino else "")
    r = client.get(url)
    assert r.status_code == 302
    alvo = urlparse(r["Location"])
    assert alvo.netloc == "login.microsoftonline.com"
    q = parse_qs(alvo.query)
    assert q["client_id"] == [CLIENTE]
    assert q["code_challenge_method"] == ["S256"]
    assert q["redirect_uri"] == ["http://testserver/api/v1/auth/microsoft/retorno/"]
    microsoft.nonce = q["nonce"][0]
    return q["state"][0]


def _erro(r):
    assert r.status_code == 302
    return parse_qs(urlparse(r["Location"]).query).get("erro", [""])[0]


def test_provedores_informa_login_microsoft(client, configurado):
    dados = client.get("/api/v1/auth/provedores/").json()
    assert dados["senha_local"] is True
    assert dados["microsoft"]["ativo"] is True


def test_sem_configuracao_login_microsoft_fica_desligado(client, db):
    assert client.get("/api/v1/auth/provedores/").json()["microsoft"]["ativo"] is False
    assert _erro(client.get("/api/v1/auth/microsoft/")) == "desativado"


def test_primeiro_login_cria_usuario_com_perfil_padrao(client, microsoft, perfis):
    estado = _iniciar(client, microsoft, destino="/repositorio")
    r = client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")
    assert r.status_code == 302 and r["Location"] == "/repositorio"
    # PKCE: o verificador enviado na troca é o que gerou o desafio
    assert microsoft.trocas[0]["code_verifier"] and microsoft.trocas[0]["code"] == "abc"

    eu = client.get("/api/v1/auth/eu/").json()
    assert eu["username"] == "fulano.tal@pm.ba.gov.br"
    assert eu["nome"] == "Fulano de Tal"
    usuario = Usuario.objects.get(username="fulano.tal@pm.ba.gov.br")
    assert usuario.id_externo == "oid-0001"
    assert not usuario.has_usable_password()
    assert list(usuario.perfis.values_list("codigo", flat=True)) == ["servidor"]
    assert EventoAuditoria.objects.filter(tipo="LOGIN", resultado="SUCESSO", usuario=usuario).exists()


def test_conta_existente_e_vinculada_pelo_email(client, microsoft, setores):
    existente = Usuario.objects.create_user(
        username="fulano", email="fulano.tal@pm.ba.gov.br", password="Senha-forte-123", setor=setores["TI"]
    )
    estado = _iniciar(client, microsoft)
    client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")
    assert client.get("/api/v1/auth/eu/").json()["username"] == "fulano"
    existente.refresh_from_db()
    assert existente.id_externo == "oid-0001"
    assert Usuario.objects.count() == 1


def test_destino_externo_e_ignorado(client, microsoft, perfis):
    estado = _iniciar(client, microsoft, destino="//site-malicioso.example")
    r = client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")
    assert r["Location"] == "/"


@pytest.mark.parametrize(
    ("ajuste", "codigo"),
    [
        ({"preferred_username": "alguem@gmail.com"}, "dominio"),
        ({"tid": "99999999-2222-3333-4444-555555555555"}, "locatario"),
        ({"aud": "outro-aplicativo"}, "token_invalido"),
        ({"iss": "https://login.microsoftonline.com/outro/v2.0"}, "token_invalido"),
        ({"exp": int(time.time()) - 3600}, "token_invalido"),
        ({"nonce": "repetido"}, "token_invalido"),
    ],
)
def test_token_que_nao_confere_e_recusado(client, microsoft, perfis, ajuste, codigo):
    microsoft.claims = ajuste
    estado = _iniciar(client, microsoft)
    assert _erro(client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")) == codigo
    assert client.get("/api/v1/auth/eu/").status_code in (401, 403)
    assert EventoAuditoria.objects.filter(tipo="LOGIN", resultado="FALHA").exists()


def test_assinatura_de_outra_chave_e_recusada(client, microsoft, perfis):
    microsoft.chave_assinatura = _chave()
    estado = _iniciar(client, microsoft)
    assert _erro(client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")) == "token_invalido"


def test_state_errado_e_recusado_sem_trocar_codigo(client, microsoft, perfis):
    _iniciar(client, microsoft)
    assert _erro(client.get("/api/v1/auth/microsoft/retorno/?code=abc&state=forjado")) == "estado_invalido"
    assert microsoft.trocas == []


def test_retorno_sem_tentativa_iniciada_e_recusado(client, microsoft, db):
    assert _erro(client.get("/api/v1/auth/microsoft/retorno/?code=abc&state=x")) == "expirado"


def test_usuario_cancelou_na_microsoft(client, microsoft, db):
    _iniciar(client, microsoft)
    assert _erro(client.get("/api/v1/auth/microsoft/retorno/?error=access_denied")) == "cancelado"


def test_sem_criacao_automatica_exige_cadastro_previo(client, microsoft, configurado, db):
    configurado.NEXO_ENTRA = {**configurado.NEXO_ENTRA, "CRIAR_USUARIOS": False}
    estado = _iniciar(client, microsoft)
    assert _erro(client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")) == "sem_cadastro"
    assert not Usuario.objects.exists()


def test_usuario_inativo_nao_entra(client, microsoft, db):
    Usuario.objects.create_user(username="x", email="fulano.tal@pm.ba.gov.br", is_active=False)
    estado = _iniciar(client, microsoft)
    assert _erro(client.get(f"/api/v1/auth/microsoft/retorno/?code=abc&state={estado}")) == "inativo"


def test_login_local_pode_ser_desligado(client, settings, setores):
    Usuario.objects.create_user(username="local", password="Senha-forte-123")
    settings.NEXO_LOGIN_LOCAL = False
    r = client.post(
        "/api/v1/auth/entrar/", {"usuario": "local", "senha": "Senha-forte-123"}, content_type="application/json"
    )
    assert r.status_code == 403
