from django.db import models


class SinalDeVida(models.Model):
    """Último sinal de cada processo de apoio (ex.: processador da fila), para o painel de saúde (ADR-023)."""

    processo = models.CharField(max_length=40, unique=True)
    atualizado_em = models.DateTimeField()
    detalhes = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.processo
