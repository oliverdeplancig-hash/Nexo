from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.comum.modelos import ModeloComDatas


class Funcao(models.TextChoices):
    """Funções administrativas globais. Não dão acesso a conteúdo documental."""

    IMPORTAR_DOCUMENTOS = "importar_documentos", "Cadastrar e importar documentos"
    GERIR_COLECOES = "gerir_colecoes", "Gerir pastas e coleções"
    GERIR_REGRAS = "gerir_regras", "Gerir regras do motor determinístico"
    GERIR_SETORES = "gerir_setores", "Gerir diretório de setores"
    ADMIN_USUARIOS = "admin_usuarios", "Administrar usuários"
    ADMIN_PERMISSOES = "admin_permissoes", "Administrar perfis e permissões (crítico)"
    VER_AUDITORIA = "ver_auditoria", "Consultar auditoria"


FUNCOES_CRITICAS = {Funcao.ADMIN_PERMISSOES, Funcao.ADMIN_USUARIOS}


class Perfil(ModeloComDatas):
    codigo = models.SlugField(max_length=50, unique=True)
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    funcoes = models.JSONField(default=list, blank=True, help_text="Lista de valores de Funcao.")

    class Meta:
        ordering = ["nome"]
        verbose_name = "perfil"
        verbose_name_plural = "perfis"

    def __str__(self):
        return self.nome


class Usuario(AbstractUser):
    """Servidor da instituição.

    `is_superuser` não é usado para acesso a documentos: o motor de permissões
    ignora esse sinalizador (ver docs/security/modelo-de-autorizacao.md).
    """

    nome_exibicao = models.CharField(max_length=150, blank=True)
    matricula = models.CharField(max_length=30, blank=True, db_index=True)
    setor = models.ForeignKey(
        "organizacao.Setor", null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios"
    )
    perfis = models.ManyToManyField(Perfil, blank=True, related_name="usuarios")

    class Meta:
        verbose_name = "usuário"
        verbose_name_plural = "usuários"

    def __str__(self):
        return self.nome_completo

    @property
    def nome_completo(self) -> str:
        return self.nome_exibicao or self.get_full_name() or self.username

    def funcoes(self) -> set[str]:
        if not self.is_active:
            return set()
        cache = getattr(self, "_cache_funcoes", None)
        if cache is None:
            cache = set()
            for perfil in self.perfis.all():
                cache.update(perfil.funcoes or [])
            self._cache_funcoes = cache
        return cache

    def tem_funcao(self, funcao: str) -> bool:
        return funcao in self.funcoes()
