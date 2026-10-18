from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificacoes")
    tipo = models.CharField(max_length=40)
    titulo = models.CharField(max_length=200)
    texto = models.CharField(max_length=500, blank=True)
    link = models.CharField(max_length=300, blank=True)
    dados = models.JSONField(default=dict, blank=True)
    lida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criada_em"]
        indexes = [models.Index(fields=["usuario", "lida"])]
