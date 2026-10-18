from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.comum.modelos import ModeloComDatas


class Acao(models.TextChoices):
    CONSULTAR = "consultar", "Consultar (aparecer em busca e IA)"
    VISUALIZAR = "visualizar", "Visualizar"
    BAIXAR = "baixar", "Baixar"
    EDITAR = "editar", "Editar"
    COMPARTILHAR = "compartilhar", "Compartilhar"
    ADMINISTRAR = "administrar", "Administrar"


class Classificacao(models.TextChoices):
    GERAL = "geral", "Geral — todos os usuários autenticados"
    SETOR = "setor", "Restrito ao setor responsável e autorizados"
    RESTRITO = "restrito", "Restrito — somente autorizações explícitas"


class AutorizacaoDocumento(ModeloComDatas):
    """Concede ações sobre um documento a um usuário, setor ou perfil.

    Exatamente um dos três destinatários deve ser informado. Compartilhamentos
    feitos por usuários também são registros desta tabela (com validade).
    """

    documento = models.ForeignKey("documentos.Documento", on_delete=models.CASCADE, related_name="autorizacoes")
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="autorizacoes"
    )
    setor = models.ForeignKey(
        "organizacao.Setor", null=True, blank=True, on_delete=models.CASCADE, related_name="autorizacoes"
    )
    perfil = models.ForeignKey(
        "contas.Perfil", null=True, blank=True, on_delete=models.CASCADE, related_name="autorizacoes"
    )
    acoes = models.JSONField(default=list)
    valido_ate = models.DateTimeField(null=True, blank=True)
    concedido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    motivo = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "autorização de documento"
        verbose_name_plural = "autorizações de documentos"
        indexes = [models.Index(fields=["documento", "usuario", "setor", "perfil"])]

    def clean(self):
        destinos = [self.usuario_id, self.setor_id, self.perfil_id]
        if sum(1 for d in destinos if d) != 1:
            raise ValidationError("Informe exatamente um destinatário: usuário, setor ou perfil.")
        invalidas = set(self.acoes) - set(Acao.values)
        if invalidas:
            raise ValidationError(f"Ações inválidas: {sorted(invalidas)}")

    def save(self, *args, **kwargs):
        self.full_clean(exclude=["documento", "concedido_por"])
        super().save(*args, **kwargs)

    @property
    def destinatario(self) -> str:
        if self.usuario_id:
            return f"usuário:{self.usuario}"
        if self.setor_id:
            return f"setor:{self.setor.sigla}"
        return f"perfil:{self.perfil.codigo}"
