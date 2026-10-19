from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

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
    path("", include("apps.manutencao.urls")),
    # Especificação OpenAPI e documentação navegável (ADR-026)
    path("esquema/", SpectacularAPIView.as_view(), name="esquema"),
    path("documentacao/", SpectacularSwaggerView.as_view(url_name="esquema"), name="documentacao"),
]

urlpatterns = [
    path("api/v1/", include(api)),
]

# O admin do Django é ferramenta de suporte técnico; a administração funcional
# é feita pelas telas do Nexo. Pode ser desligado em produção.
if settings.DEBUG or getattr(settings, "NEXO_ADMIN_DJANGO", False):
    urlpatterns.append(path("django-admin/", admin.site.urls))

# Telas do Nexo servidas pelo próprio backend (servidor de rede no Windows, ADR-019): qualquer rota que não seja
# da API devolve o index.html do React. Arquivos (assets, sw.js, ícones) saem antes, pelo WhiteNoise.
if settings.NEXO_SERVIR_FRONTEND:
    from apps.comum.views import aplicativo

    urlpatterns.append(re_path(r"^(?!api/|ws/|static/|django-admin/).*$", aplicativo, name="aplicativo"))
