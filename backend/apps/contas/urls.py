from django.urls import path
from rest_framework.routers import DefaultRouter

from . import recuperacao, views

router = DefaultRouter()
router.register("usuarios", views.UsuarioViewSet, basename="usuario")
router.register("perfis", views.PerfilViewSet, basename="perfil")

urlpatterns = [
    path("auth/csrf/", views.csrf, name="auth-csrf"),
    path("auth/entrar/", views.entrar, name="auth-entrar"),
    path("auth/provedores/", views.provedores, name="auth-provedores"),
    path("auth/microsoft/", views.microsoft_iniciar, name="auth-microsoft"),
    path("auth/microsoft/retorno/", views.microsoft_retorno, name="auth-microsoft-retorno"),
    path("auth/sair/", views.sair, name="auth-sair"),
    path("auth/eu/", views.eu, name="auth-eu"),
    path("auth/trocar-senha/", views.trocar_senha, name="auth-trocar-senha"),
    path("auth/esqueci-senha/", recuperacao.esqueci_senha, name="auth-esqueci-senha"),
    path("auth/redefinir-senha/", recuperacao.redefinir_senha, name="auth-redefinir-senha"),
    path("funcoes/", views.funcoes, name="funcoes"),
    *router.urls,
]
