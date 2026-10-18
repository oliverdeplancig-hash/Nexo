from django.conf import settings
from django.contrib import admin
from django.urls import include, path

api = [
    path("", include("apps.contas.urls")),
    path("", include("apps.organizacao.urls")),
    path("", include("apps.acesso.urls")),
    path("", include("apps.documentos.urls")),
    path("", include("apps.ingestao.urls")),
    path("", include("apps.busca.urls")),
    path("", include("apps.motor.urls")),
    path("", include("apps.conversas.urls")),
    path("", include("apps.auditoria.urls")),
    path("", include("apps.notificacoes.urls")),
    path("", include("apps.comum.urls")),
]

urlpatterns = [
    path("api/v1/", include(api)),
]

# O admin do Django é ferramenta de suporte técnico; a administração funcional
# é feita pelas telas do Nexo. Pode ser desligado em produção.
if settings.DEBUG or getattr(settings, "NEXO_ADMIN_DJANGO", False):
    urlpatterns.append(path("django-admin/", admin.site.urls))
