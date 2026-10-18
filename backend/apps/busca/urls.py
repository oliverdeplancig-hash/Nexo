from django.urls import path

from . import views

urlpatterns = [path("busca/", views.buscar, name="busca")]
