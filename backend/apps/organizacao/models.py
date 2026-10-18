from django.db import models

from apps.comum.modelos import ModeloComDatas


class Setor(ModeloComDatas):
    """Unidade organizacional. Também alimenta o diretório de setores e contatos.

    Todos os dados de contato são cadastrados pela instituição: o Nexo nunca
    inventa contatos, atribuições ou nomes de servidores.
    """

    nome = models.CharField(max_length=200, unique=True)
    sigla = models.CharField(max_length=30, unique=True)
    setor_superior = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="subordinados"
    )
    descricao = models.TextField("descrição resumida", blank=True)
    competencias = models.TextField("competências", blank=True)
    tipos_demanda = models.JSONField("tipos de demanda atendidos", default=list, blank=True)
    servicos = models.JSONField("serviços prestados", default=list, blank=True)
    procedimentos_relacionados = models.JSONField(default=list, blank=True)
    canal_contato = models.CharField("canal institucional de contato", max_length=255, blank=True)
    horario_atendimento = models.CharField(max_length=120, blank=True)
    orientacao_acesso = models.TextField("orientação para solicitar informações ou acesso", blank=True)
    palavras_chave = models.JSONField(default=list, blank=True)
    contato_visivel_para_todos = models.BooleanField(
        default=True,
        help_text="Se desmarcado, o canal de contato só aparece para membros do próprio setor.",
    )
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ["nome"]
        verbose_name = "setor"
        verbose_name_plural = "setores"

    def __str__(self):
        return f"{self.sigla} — {self.nome}"
