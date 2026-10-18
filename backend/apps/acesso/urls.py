from django.urls import path

from . import views

urlpatterns = [
    path("acesso/acoes/", views.acoes, name="acesso-acoes"),
    path("acesso/documentos/<int:documento_id>/minhas/", views.minhas_permissoes, name="acesso-minhas"),
    path("acesso/documentos/<int:documento_id>/matriz/", views.matriz, name="acesso-matriz"),
    path("acesso/autorizacoes/<int:autorizacao_id>/", views.revogar, name="acesso-revogar"),
]
