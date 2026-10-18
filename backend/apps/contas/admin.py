from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Perfil, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Nexo", {"fields": ("nome_exibicao", "matricula", "setor", "perfis")}),)
    list_display = ("username", "nome_exibicao", "setor", "is_active")
    list_filter = ("is_active", "setor", "perfis")


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nome")
