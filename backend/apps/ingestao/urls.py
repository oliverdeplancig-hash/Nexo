from django.urls import path

from . import views

urlpatterns = [
    path("ingestao/importar/", views.importar, name="ingestao-importar"),
    path("ingestao/fila/", views.fila, name="ingestao-fila"),
    path("ingestao/documentos/<int:documento_id>/nova-versao/", views.nova_versao, name="ingestao-nova-versao"),
    path("ingestao/documentos/<int:documento_id>/reprocessar/", views.reprocessar, name="ingestao-reprocessar"),
]
