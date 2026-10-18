from django.urls import path

from . import views

urlpatterns = [path("manutencao/copias/", views.situacao_copias, name="copias-situacao")]
