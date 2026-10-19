"""Credenciais geradas pelo Nexo (ADR-018).

- Senha temporária forte, gerada com `secrets`, válida por NEXO_SENHA_TEMPORARIA_HORAS (padrão 72 h).
- Enviada por e-mail quando NEXO_EMAIL_HOST está configurado; senão, mostrada uma única vez a quem cadastrou.
- No primeiro acesso a pessoa é obrigada a criar a própria senha; até lá, a API só atende troca de senha,
  "quem sou eu" e sair (middleware abaixo).
- A senha nunca vai para a auditoria nem para logs.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.http import JsonResponse
from django.utils import timezone

from .models import Usuario

logger = logging.getLogger("nexo.credenciais")

# Sem caracteres ambíguos (0/O, 1/l/I) para quem digita a senha a partir do e-mail.
_MAIUSCULAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_MINUSCULAS = "abcdefghijkmnopqrstuvwxyz"
_DIGITOS = "23456789"
_SIMBOLOS = "@#%+=?!"


def gerar_senha(tamanho: int = 14) -> str:
    gerador = secrets.SystemRandom()
    obrigatorios = [secrets.choice(c) for c in (_MAIUSCULAS, _MINUSCULAS, _DIGITOS, _SIMBOLOS)]
    todos = _MAIUSCULAS + _MINUSCULAS + _DIGITOS + _SIMBOLOS
    resto = [secrets.choice(todos) for _ in range(tamanho - len(obrigatorios))]
    caracteres = obrigatorios + resto
    gerador.shuffle(caracteres)
    return "".join(caracteres)


def email_configurado() -> bool:
    return bool(getattr(settings, "NEXO_EMAIL_HOST", ""))


@dataclass
class Credenciais:
    usuario: str
    senha_temporaria: str
    expira_em: object
    enviado_por_email: bool
    destino_email: str
    aviso: str


def emitir(usuario: Usuario, request=None, motivo: str = "cadastro") -> Credenciais:
    """Gera senha temporária, grava e tenta enviar por e-mail. Devolve os dados para mostrar UMA vez."""
    from apps.auditoria.servico import registrar

    senha = gerar_senha()
    validate_password(senha, usuario)
    usuario.set_password(senha)
    usuario.senha_temporaria = True
    usuario.senha_temporaria_expira_em = timezone.now() + timedelta(hours=settings.NEXO_CREDENCIAIS["VALIDADE_HORAS"])
    usuario.save(update_fields=["password", "senha_temporaria", "senha_temporaria_expira_em"])

    enviado, aviso = False, ""
    if not usuario.email:
        aviso = "O usuário não tem e-mail cadastrado. Entregue a senha por outro meio seguro."
    elif not email_configurado():
        aviso = "O envio de e-mail não está configurado neste servidor. Entregue a senha por outro meio seguro."
    else:
        try:
            send_mail(
                "Seu acesso ao Nexo",
                _texto_email(usuario, senha, request),
                None,
                [usuario.email],
                fail_silently=False,
            )
            enviado = True
        except Exception as erro:  # SMTP fora do ar não pode impedir o cadastro
            logger.warning("Falha ao enviar credenciais para %s: %s", usuario.username, erro.__class__.__name__)
            aviso = "Não foi possível enviar o e-mail agora. Entregue a senha por outro meio seguro ou tente reenviar."

    registrar(
        request,
        "ADMIN_USUARIO",
        objeto=usuario,
        detalhes={"acao": "emitir_credenciais", "motivo": motivo, "enviado_por_email": enviado},
    )
    return Credenciais(
        usuario=usuario.username,
        senha_temporaria=senha,
        expira_em=usuario.senha_temporaria_expira_em,
        enviado_por_email=enviado,
        destino_email=usuario.email if enviado else "",
        aviso=aviso,
    )


def _url_publica(request) -> str:
    url = settings.NEXO_CREDENCIAIS["URL_PUBLICA"]
    if url:
        return url.rstrip("/")
    if request is not None and hasattr(request, "build_absolute_uri"):
        return request.build_absolute_uri("/").rstrip("/")
    return ""


def _texto_email(usuario: Usuario, senha: str, request) -> str:
    validade = timezone.localtime(usuario.senha_temporaria_expira_em).strftime("%d/%m/%Y às %H:%M")
    nome = usuario.nome_completo
    endereco = _url_publica(request)
    linhas = [
        f"Olá, {nome}.",
        "",
        "Seu acesso ao Nexo foi criado.",
        "",
        *([f"Endereço: {endereco}"] if endereco else []),
        f"Usuário: {usuario.username}",
        f"Senha temporária: {senha}",
        "",
        f"A senha temporária vale até {validade}. No primeiro acesso você vai criar a sua própria senha.",
        "",
        "Não compartilhe esta mensagem. Se você não esperava este acesso, avise o administrador do sistema.",
    ]
    return "\n".join(linhas)


def temporaria_expirada(usuario: Usuario) -> bool:
    return bool(
        usuario.senha_temporaria
        and usuario.senha_temporaria_expira_em
        and usuario.senha_temporaria_expira_em < timezone.now()
    )


class ExigeTrocaDeSenha:
    """Enquanto a senha for temporária, a API só atende o necessário para trocá-la."""

    PERMITIDOS = ("/api/v1/auth/eu/", "/api/v1/auth/trocar-senha/", "/api/v1/auth/sair/", "/api/v1/auth/csrf/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        usuario = getattr(request, "user", None)
        if (
            request.path.startswith("/api/")
            and usuario is not None
            and usuario.is_authenticated
            and getattr(usuario, "senha_temporaria", False)
            and request.path not in self.PERMITIDOS
        ):
            return JsonResponse({"detail": "Crie a sua senha para continuar.", "codigo": "trocar_senha"}, status=403)
        return self.get_response(request)
