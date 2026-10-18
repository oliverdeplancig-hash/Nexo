from django.db import models


class EtapaProcessamento(models.Model):
    """Histórico das etapas de processamento de cada documento (tela 07)."""

    class Situacao(models.TextChoices):
        OK = "ok", "Concluída"
        AVISO = "aviso", "Concluída com aviso"
        ERRO = "erro", "Erro"

    documento = models.ForeignKey("documentos.Documento", on_delete=models.CASCADE, related_name="etapas")
    etapa = models.CharField(max_length=20)
    situacao = models.CharField(max_length=10, choices=Situacao.choices)
    mensagem = models.CharField(max_length=500, blank=True)
    ocorrido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["documento", "id"]
