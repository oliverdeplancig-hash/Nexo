"""Link de ativação: a pessoa cria a própria senha, sem receber senha por e-mail (ADR-027).

- No cadastro (ou quando o administrador pede um novo acesso), a conta fica **sem senha utilizável** e a
  pessoa recebe por e-mail um link de uso único que vale `NEXO_ATIVACAO_HORAS` (72 h).
- Pelo link, ela cria a senha (regras do Django). Nenhuma senha passa pelo e-mail nem pela tela de quem
  cadastrou — é a evolução prevista na ADR-018.
- Exige SMTP configurado e e-mail cadastrado; sem isso, continua valendo a senha temporária (ADR-018).
- O token é assinado, calculado sobre a senha atual (deixa de valer ao ser usado) e expira; nada é gravado.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.encoding import force_bytes, force_str
from django.utils.http import base36_to_int, urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.auditoria.servico import registrar

from .credenciais import _url_publica, email_configurado
from .models import Usuario
from .recuperacao import LimiteRecuperacao

logger = logging.getLogger("nexo.credenciais")


class _GeradorAtivacao(PasswordResetTokenGenerator):
    key_salt = "nexo.contas.ativacao"

    def _make_hash_value(self, usuario, momento):
        return f"{usuario.pk}{usuario.password}{usuario.is_active}{momento}"

    def check_token(self, usuario, token):
        """Como o do Django, mas com validade própria (horas, não a da recuperação de senha)."""
        if not (usuario and token) or "-" not in token:
            return False
        try:
            momento = base36_to_int(token.split("-")[0])
        except ValueError:
            return False
        if not any(
            constant_time_compare(self._make_token_with_timestamp(usuario, momento, segredo), token)
            for segredo in [self.secret, *self.secret_fallbacks]
        ):
            return False
        return (self._num_seconds(self._now()) - momento) <= horas() * 3600


gerador = _GeradorAtivacao()


def horas() -> int:
    return settings.NEXO_ATIVACAO_HORAS


def disponivel() -> bool:
    return bool(settings.NEXO_LOGIN_LOCAL and email_configurado())


@dataclass
class Envio:
    enviado: bool
    destino_email: str
    expira_em: object
    aviso: str


def enviar_link(usuario: Usuario, request=None, motivo: str = "cadastro") -> Envio:
    """Deixa a conta sem senha e envia o link. Chamado por quem administra usuários."""
    if not disponivel() or not usuario.email:
        return Envio(False, "", None, "O link exige o envio de e-mail configurado e um e-mail cadastrado.")
    usuario.set_unusable_password()
    usuario.senha_temporaria = False
    usuario.senha_temporaria_expira_em = None
    usuario.save(update_fields=["password", "senha_temporaria", "senha_temporaria_expira_em"])
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    link = f"{_url_publica(request)}/ativar-conta?u={uid}&t={gerador.make_token(usuario)}"
    expira = timezone.now() + timedelta(hours=horas())
    corpo = "\n".join(
        [
            f"Olá, {usuario.nome_completo}.",
            "",
            "Seu acesso ao Nexo foi liberado. Para criar a sua senha, abra o link abaixo:",
            "",
            link,
            "",
            f"Usuário: {usuario.username}",
            f"O link vale até {timezone.localtime(expira):%d/%m/%Y às %H:%M} e pode ser usado uma vez.",
            "",
            "Se você não esperava este acesso, avise o administrador do sistema.",
        ]
    )
    try:
        send_mail("Crie sua senha do Nexo", corpo, None, [usuario.email], fail_silently=False)
        enviado, aviso = True, ""
    except Exception as erro:  # SMTP fora do ar: o administrador pode reenviar ou gerar senha temporária
        logger.warning("Falha ao enviar link de ativação para %s: %s", usuario.username, erro.__class__.__name__)
        enviado, aviso = (
            False,
            "Não foi possível enviar o e-mail agora. Tente reenviar o link ou gere uma senha temporária.",
        )
    registrar(
        request,
        "ADMIN_USUARIO",
        objeto=usuario,
        detalhes={"acao": "enviar_link_ativacao", "motivo": motivo, "enviado_por_email": enviado},
    )
    return Envio(enviado, usuario.email if enviado else "", expira, aviso)


def _usuario_do_link(uid: str, token: str) -> Usuario | None:
    try:
        usuario = Usuario.objects.get(pk=force_str(urlsafe_base64_decode(uid)), is_active=True)
    except (TypeError, ValueError, OverflowError, Usuario.DoesNotExist):
        return None
    return usuario if gerador.check_token(usuario, token) else None


@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LimiteRecuperacao])
def ativar_conta(request):
    """{"u", "t"} confere o link; {"u", "t", "nova_senha"} cria a senha."""
    usuario = _usuario_do_link(str(request.data.get("u") or ""), str(request.data.get("t") or ""))
    if usuario is None:
        return Response(
            {"detail": "Este link não vale mais: já foi usado ou expirou. Peça um novo ao administrador do sistema."},
            status=400,
        )
    nova = request.data.get("nova_senha")
    if nova is None:
        return Response({"valido": True, "usuario": usuario.username})
    try:
        validate_password(nova, usuario)
    except DjangoValidationError as erro:
        return Response({"nova_senha": list(erro.messages)}, status=400)
    usuario.set_password(nova)  # o link deixa de valer
    usuario.senha_alterada_em = timezone.now()
    usuario.save(update_fields=["password", "senha_alterada_em"])
    registrar(request, "ADMIN_USUARIO", usuario=usuario, objeto=usuario, detalhes={"acao": "ativar_conta"})
    return Response({"detail": "Senha criada. Entre com o seu usuário e a nova senha."})
