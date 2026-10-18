"""Login institucional pela conta Microsoft (Microsoft Entra ID) — ver docs/adr/ADR-010.

Fluxo OpenID Connect "authorization code" com PKCE e cliente confidencial:

1. `/auth/microsoft/` guarda state, nonce e o verificador PKCE na sessão e redireciona para a Microsoft;
2. a Microsoft devolve o usuário em `/auth/microsoft/retorno/` com um código de uso único;
3. o código é trocado pelo id_token, cuja assinatura, emissor, público, validade, nonce e locatário
   (tenant) são verificados antes de qualquer login.

Somente dados de identidade (nome e e-mail) trafegam com a Microsoft; nenhum documento sai da rede.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
import jwt
from django.conf import settings
from django.db import transaction

from .models import Perfil, Usuario

logger = logging.getLogger("nexo.entra")

CHAVE_SESSAO = "nexo_entra"
VALIDADE_TENTATIVA_SEGUNDOS = 10 * 60
_CACHE_DESCOBERTA: dict[str, tuple[float, dict]] = {}
_CACHE_SEGUNDOS = 60 * 60


class FalhaEntra(Exception):
    """Login recusado. `codigo` vai para a tela de entrada, que mostra a mensagem."""

    def __init__(self, codigo: str, detalhe: str = ""):
        super().__init__(detalhe or codigo)
        self.codigo = codigo
        self.detalhe = detalhe


def config() -> dict:
    return settings.NEXO_ENTRA


def ativo() -> bool:
    c = config()
    return bool(c["TENANT_ID"] and c["CLIENT_ID"] and c["CLIENT_SECRET"])


# --------------------------------------------------------------------------
# HTTP (isolado para os testes)
# --------------------------------------------------------------------------
def _get_json(url: str) -> dict:
    resposta = httpx.get(url, timeout=10)
    resposta.raise_for_status()
    return resposta.json()


def _post_form(url: str, dados: dict) -> dict:
    resposta = httpx.post(url, data=dados, timeout=15)
    try:
        corpo = resposta.json()
    except ValueError:
        corpo = {}
    if resposta.status_code >= 400:
        raise FalhaEntra("troca_codigo", corpo.get("error_description", "")[:300] or f"HTTP {resposta.status_code}")
    return corpo


def descoberta() -> dict:
    """Metadados OpenID do locatário (endpoints, emissor e chaves), em cache por 1 hora."""
    c = config()
    url = f"{c['AUTORIDADE'].rstrip('/')}/{c['TENANT_ID']}/v2.0/.well-known/openid-configuration"
    agora = time.monotonic()
    em_cache = _CACHE_DESCOBERTA.get(url)
    if em_cache and agora - em_cache[0] < _CACHE_SEGUNDOS:
        return em_cache[1]
    try:
        dados = _get_json(url)
    except httpx.HTTPError as erro:
        raise FalhaEntra("indisponivel", str(erro)) from erro
    _CACHE_DESCOBERTA[url] = (agora, dados)
    return dados


def limpar_cache():
    _CACHE_DESCOBERTA.clear()


# --------------------------------------------------------------------------
# Etapa 1: redirecionar para a Microsoft
# --------------------------------------------------------------------------
def _b64url(dados: bytes) -> str:
    return base64.urlsafe_b64encode(dados).rstrip(b"=").decode()


def url_retorno(request) -> str:
    return config()["REDIRECT_URI"] or request.build_absolute_uri("/api/v1/auth/microsoft/retorno/")


def iniciar(request, destino: str = "/") -> str:
    """Prepara a tentativa na sessão e devolve a URL de autorização da Microsoft."""
    meta = descoberta()
    verificador = _b64url(secrets.token_bytes(48))
    tentativa = {
        "state": secrets.token_urlsafe(32),
        "nonce": secrets.token_urlsafe(32),
        "verificador": verificador,
        "destino": destino if destino.startswith("/") and not destino.startswith("//") else "/",
        "criada": time.time(),
    }
    request.session[CHAVE_SESSAO] = tentativa
    parametros = {
        "client_id": config()["CLIENT_ID"],
        "response_type": "code",
        "redirect_uri": url_retorno(request),
        "response_mode": "query",
        "scope": "openid profile email",
        "state": tentativa["state"],
        "nonce": tentativa["nonce"],
        "code_challenge": _b64url(hashlib.sha256(verificador.encode()).digest()),
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{meta['authorization_endpoint']}?{urlencode(parametros)}"


# --------------------------------------------------------------------------
# Etapa 2: retorno da Microsoft
# --------------------------------------------------------------------------
@dataclass
class Identidade:
    oid: str
    tid: str
    email: str
    nome: str


def concluir(request) -> tuple[Usuario, str]:
    """Valida o retorno e devolve (usuário, destino). Lança FalhaEntra se algo não confere."""
    tentativa = request.session.pop(CHAVE_SESSAO, None)
    if request.GET.get("error"):
        codigo = "cancelado" if request.GET["error"] == "access_denied" else "microsoft"
        raise FalhaEntra(codigo, request.GET.get("error_description", "")[:300])
    if not tentativa or time.time() - tentativa.get("criada", 0) > VALIDADE_TENTATIVA_SEGUNDOS:
        raise FalhaEntra("expirado")
    if not secrets.compare_digest(request.GET.get("state", ""), tentativa["state"]):
        raise FalhaEntra("estado_invalido")
    codigo = request.GET.get("code", "")
    if not codigo:
        raise FalhaEntra("microsoft", "Retorno sem código de autorização.")

    meta = descoberta()
    c = config()
    tokens = _post_form(
        meta["token_endpoint"],
        {
            "client_id": c["CLIENT_ID"],
            "client_secret": c["CLIENT_SECRET"],
            "grant_type": "authorization_code",
            "code": codigo,
            "redirect_uri": url_retorno(request),
            "code_verifier": tentativa["verificador"],
            "scope": "openid profile email",
        },
    )
    identidade = validar_id_token(tokens.get("id_token", ""), tentativa["nonce"], meta)
    return vincular_usuario(identidade), tentativa["destino"]


def validar_id_token(id_token: str, nonce: str, meta: dict) -> Identidade:
    if not id_token:
        raise FalhaEntra("token_invalido", "A Microsoft não devolveu id_token.")
    c = config()
    try:
        cabecalho = jwt.get_unverified_header(id_token)
        chaves = jwt.PyJWKSet.from_dict(_get_json(meta["jwks_uri"]))
        chave = next((k for k in chaves.keys if k.key_id == cabecalho.get("kid")), None)
        if chave is None:
            raise FalhaEntra("token_invalido", "Chave de assinatura desconhecida.")
        claims = jwt.decode(
            id_token,
            key=chave.key,
            algorithms=["RS256"],
            audience=c["CLIENT_ID"],
            issuer=meta["issuer"],
            leeway=60,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
    except FalhaEntra:
        raise
    except (jwt.PyJWTError, httpx.HTTPError, KeyError, json.JSONDecodeError) as erro:
        raise FalhaEntra("token_invalido", str(erro)[:300]) from erro

    if not secrets.compare_digest(str(claims.get("nonce", "")), nonce):
        raise FalhaEntra("token_invalido", "nonce não confere.")
    tid = str(claims.get("tid", ""))
    # Com TENANT_ID em forma de GUID, o locatário do token tem de ser exatamente esse.
    if _parece_guid(c["TENANT_ID"]) and tid.lower() != c["TENANT_ID"].lower():
        raise FalhaEntra("locatario", f"tid {tid}")
    oid = str(claims.get("oid", "") or claims.get("sub", ""))
    email = str(claims.get("preferred_username") or claims.get("email") or "").strip().lower()
    if not oid or "@" not in email:
        raise FalhaEntra("token_invalido", "Token sem identificação do usuário.")
    dominios = [d.lower().lstrip("@") for d in c["DOMINIOS"]]
    if dominios and email.rsplit("@", 1)[1] not in dominios:
        raise FalhaEntra("dominio", email)
    return Identidade(oid=oid, tid=tid, email=email, nome=str(claims.get("name", ""))[:150])


def _parece_guid(valor: str) -> bool:
    partes = valor.split("-")
    return [len(p) for p in partes] == [8, 4, 4, 4, 12]


@transaction.atomic
def vincular_usuario(identidade: Identidade) -> Usuario:
    """Encontra (ou cria) o usuário do Nexo da identidade Microsoft.

    Ordem: vínculo já gravado (oid) → conta existente com o mesmo e-mail/usuário → criação automática
    (se habilitada), com o perfil padrão e sem setor: o servidor vê apenas documentos de acesso geral até
    um administrador definir setor e perfis.
    """
    usuario = Usuario.objects.select_for_update().filter(id_externo=identidade.oid).first()
    if usuario is None:
        usuario = (
            Usuario.objects.select_for_update()
            .filter(id_externo__isnull=True)
            .filter(email__iexact=identidade.email)
            .first()
            or Usuario.objects.select_for_update()
            .filter(id_externo__isnull=True, username__iexact=identidade.email)
            .first()
        )
        if usuario is not None:
            usuario.id_externo = identidade.oid
            usuario.save(update_fields=["id_externo"])
    if usuario is None:
        if not config()["CRIAR_USUARIOS"]:
            raise FalhaEntra("sem_cadastro", identidade.email)
        if Usuario.objects.filter(username__iexact=identidade.email).exists():
            raise FalhaEntra("conflito", identidade.email)
        usuario = Usuario(
            username=identidade.email,
            email=identidade.email,
            nome_exibicao=identidade.nome,
            id_externo=identidade.oid,
        )
        usuario.set_unusable_password()
        usuario.save()
        perfil = Perfil.objects.filter(codigo=config()["PERFIL_PADRAO"]).first()
        if perfil:
            usuario.perfis.add(perfil)
        logger.info("Usuário criado pelo login Microsoft: %s", identidade.email)
    if not usuario.is_active:
        raise FalhaEntra("inativo", identidade.email)
    alterou = []
    if identidade.nome and not usuario.nome_exibicao:
        usuario.nome_exibicao = identidade.nome
        alterou.append("nome_exibicao")
    if not usuario.email:
        usuario.email = identidade.email
        alterou.append("email")
    if alterou:
        usuario.save(update_fields=alterou)
    return usuario
