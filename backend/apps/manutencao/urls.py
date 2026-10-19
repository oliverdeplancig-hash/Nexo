from django.urls import path

from . import views

urlpatterns = [
    path("manutencao/copias/", views.situacao_copias, name="copias-situacao"),
    path("manutencao/saude/", views.saude_sistema, name="saude-sistema"),
]
