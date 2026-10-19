"""Recuperação de senha pelo próprio usuário (ADR-024).

- "Esqueci minha senha": a pessoa informa o usuário ou o e-mail; se a conta puder recuperar a senha, recebe por
  e-mail um link de uso único que vale `NEXO_RECUPERACAO_MINUTOS` (60). A resposta é **sempre a mesma**, exista
  ou não a conta (não revela quem tem cadastro), e o envio acontece fora da requisição (sem diferença de tempo).
- Só para contas locais ativas, com e-mail cadastrado e senha utilizável, com o login local ligado e o SMTP
  configurado. Conta da Microsoft (ADR-010) recupera a senha na Microsoft.
- O link usa o gerador de tokens do Django: assinado com a chave secreta, deixa de valer quando a senha muda
  (uso único) e quando expira. Nada é guardado no banco.
- Limites: por endereço (NEXO_LIMITE_RECUPERACAO, 5/h) e por conta (3 e-mails por hora).
- Ao redefinir: valida a senha com as regras do Django, encerra as outras sessões, avisa por e-mail que a senha
  foi alterada e registra na auditoria, sempre sem a senha.
"""

from __future__ import annotations

import logging
import threading

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.cache import cache
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.db.models import Q
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle

from apps.auditoria.servico import registrar

from .credenciais import _url_publica, email_configurado
from .models import Usuario

logger = logging.getLogger("nexo.credenciais")

MENSAGEM_ENVIADA = (
    "Se houver uma conta com esses dados que possa recuperar a senha, enviamos um link para o e-mail cadastrado. "
    "Ele vale por pouco tempo. Não recebeu? Confira a caixa de spam ou procure o administrador do sistema."
)
ENVIOS_POR_HORA = 3


class _Gerador(PasswordResetTokenGenerator):
    key_salt = "nexo.contas.recuperacao"

    def _make_hash_value(self, usuario, momento):
        # Muda quando a senha muda (uso único) ou a conta é desativada.
        return f"{usuario.pk}{usuario.password}{usuario.is_active}{momento}"


gerador = _Gerador()


class LimiteRecuperacao(AnonRateThrottle):
    scope = "recuperacao"


def disponivel() -> bool:
    return bool(settings.NEXO_LOGIN_LOCAL and email_configurado())


def _elegivel(usuario: Usuario) -> bool:
    return bool(usuario.is_active and usuario.email and usuario.has_usable_password())


def _procurar(identificacao: str) -> Usuario | None:
    texto = identificacao.strip()
    if not texto or len(texto) > 254:
        return None
    candidatos = list(Usuario.objects.filter(Q(username__iexact=texto) | Q(email__iexact=texto))[:2])
    return candidatos[0] if len(candidatos) == 1 else None  # e-mail repetido: não adivinha a conta


def _enviar(assunto: str, corpo: str, destino: str) -> None:
    def _tarefa():
        try:
            send_mail(assunto, corpo, None, [destino], fail_silently=False)
        except Exception as erro:  # SMTP fora do ar: registra sem o endereço
            logger.warning("Falha no envio de e-mail de recuperação: %s", erro.__class__.__name__)

    if settings.NEXO_RECUPERACAO["ENVIO_EM_SEGUNDO_PLANO"]:
        threading.Thread(target=_tarefa, daemon=True).start()
    else:
        _tarefa()


def link(usuario: Usuario, request=None) -> str:
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    return f"{_url_publica(request)}/redefinir-senha?u={uid}&t={gerador.make_token(usuario)}"


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LimiteRecuperacao])
def esqueci_senha(request):
    """{"identificacao": usuário ou e-mail} → sempre a mesma resposta."""
    if not disponivel():
        return Response(
            {"detail": "A recuperação de senha pelo e-mail não está ativa. Procure o administrador do sistema."},
            status=400,
        )
    usuario = _procurar(str(request.data.get("identificacao") or ""))
    if usuario is not None and _elegivel(usuario):
        chave = f"nexo:recuperacao:{usuario.pk}"
        envios = cache.get(chave, 0)
        if envios < ENVIOS_POR_HORA:
            cache.set(chave, envios + 1, 3600)
            minutos = settings.NEXO_RECUPERACAO["MINUTOS"]
            corpo = "\n".join(
                [
                    f"Olá, {usuario.nome_completo}.",
                    "",
                    "Recebemos um pedido para criar uma nova senha de acesso ao Nexo.",
                    f"Para continuar, abra o link abaixo em até {minutos} minutos:",
                    "",
                    link(usuario, request),
                    "",
                    f"Usuário: {usuario.username}",
                    "",
                    "Se não foi você, ignore esta mensagem: sua senha continua a mesma.",
                ]
            )
            _enviar("Nova senha do Nexo", corpo, usuario.email)
            registrar(request, "ADMIN_USUARIO", usuario=usuario, objeto=usuario, detalhes={"acao": "pedir_recuperacao"})
    return Response({"detail": MENSAGEM_ENVIADA})


def _usuario_do_link(uid: str, token: str) -> Usuario | None:
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        usuario = Usuario.objects.get(pk=pk)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None
    if not _elegivel(usuario) or not gerador.check_token(usuario, token):
        return None
    return usuario


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LimiteRecuperacao])
def redefinir_senha(request):
    """{"u", "t", "nova_senha"}; sem "nova_senha", só confere se o link ainda vale."""
    if not disponivel():
        return Response({"detail": "A recuperação de senha não está ativa."}, status=400)
    usuario = _usuario_do_link(str(request.data.get("u") or ""), str(request.data.get("t") or ""))
    if usuario is None:
        return Response(
            {"detail": "Este link não vale mais: já foi usado ou expirou. Peça um novo em “Esqueci minha senha”."},
            status=400,
        )
    nova = request.data.get("nova_senha")
    if nova is None:
        return Response({"valido": True, "usuario": usuario.username})
    try:
        validate_password(nova, usuario)
    except DjangoValidationError as erro:
        return Response({"nova_senha": list(erro.messages)}, status=400)
    usuario.set_password(nova)  # invalida o link e as sessões abertas (o hash da sessão depende da senha)
    usuario.senha_temporaria = False
    usuario.senha_temporaria_expira_em = None
    usuario.senha_alterada_em = timezone.now()
    usuario.save(update_fields=["password", "senha_temporaria", "senha_temporaria_expira_em", "senha_alterada_em"])
    registrar(request, "ADMIN_USUARIO", usuario=usuario, objeto=usuario, detalhes={"acao": "recuperar_senha"})
    _enviar(
        "Sua senha do Nexo foi alterada",
        f"Olá, {usuario.nome_completo}.\n\nA senha da sua conta no Nexo ({usuario.username}) acabou de ser alterada "
        "pelo link de recuperação. Se não foi você, avise imediatamente o administrador do sistema.",
        usuario.email,
    )
    return Response({"detail": "Senha criada. Entre com a nova senha."})
