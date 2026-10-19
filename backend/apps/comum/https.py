"""Redireciona HTTP para HTTPS no servidor de rede Windows (ADR-019), mantendo o nome usado pelo navegador
e trocando só a porta (o SECURE_SSL_REDIRECT do Django repetiria a porta HTTP)."""

from django.conf import settings
from django.http import HttpResponsePermanentRedirect

ISENTOS = ("/api/v1/saude/",)  # monitoramento simples continua respondendo em HTTP


class RedirecionaParaHttps:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.NEXO_REDIRECIONAR_HTTPS and not request.is_secure() and request.path not in ISENTOS:
            nome = request.get_host().rsplit(":", 1)[0] if not request.get_host().endswith("]") else request.get_host()
            porta = settings.NEXO_PORTA_HTTPS
            destino = f"https://{nome}{'' if porta == 443 else f':{porta}'}{request.get_full_path()}"
            return HttpResponsePermanentRedirect(destino)
        return self.get_response(request)
