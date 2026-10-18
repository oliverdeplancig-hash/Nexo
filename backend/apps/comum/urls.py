from django.urls import path

from . import views

urlpatterns = [
    path("saude/", views.saude, name="saude"),
    path("status/", views.status_servicos, name="status-servicos"),
]
