from django.conf import settings
from django.db import models

from apps.comum.modelos import ModeloComDatas


class TipoRegra(models.TextChoices):
    PROCEDIMENTO = "procedimento", "Procedimento (passo a passo)"
    FAQ = "faq", "Pergunta frequente"
    ROTEAMENTO = "roteamento", "Encaminhamento a setor"
    ORIENTACAO_ACESSO = "orientacao_acesso", "Orientação para solicitar acesso"


class StatusRegra(models.TextChoices):
    RASCUNHO = "rascunho", "Rascunho"
    PUBLICADA = "publicada", "Publicada"
    ARQUIVADA = "arquivada", "Arquivada"


class Regra(ModeloComDatas):
    """Resposta curada e aprovada, devolvida sem LLM quando a pergunta casa.

    O casamento é determinístico (ver apps.motor.motor). A mesma pergunta,
    com o mesmo conjunto de regras publicadas, produz sempre a mesma resposta.
    """

    codigo = models.CharField(max_length=20, unique=True, help_text="Ex.: MD-001")
    titulo = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=TipoRegra.choices, default=TipoRegra.FAQ)

    frases_exemplo = models.JSONField(
        default=list, help_text="Perguntas que devem disparar a regra (quanto mais variações, melhor)."
    )
    palavras_chave = models.JSONField(default=list, blank=True, help_text="Reforçam a pontuação.")
    termos_obrigatorios = models.JSONField(
        default=list, blank=True, help_text="Se informados, TODOS precisam aparecer na pergunta."
    )
    termos_excludentes = models.JSONField(
        default=list, blank=True, help_text="Se algum aparecer, a regra não se aplica."
    )
    padroes_regex = models.JSONField(default=list, blank=True, help_text="Expressões regulares (casamento direto).")

    resposta = models.TextField(help_text="Markdown. Variáveis: {usuario_nome}, {setor_usuario}, {setor_responsavel}.")
    etapas = models.JSONField(default=list, blank=True, help_text='Lista de {"titulo": ..., "descricao": ...}.')
    setor_responsavel = models.ForeignKey(
        "organizacao.Setor", null=True, blank=True, on_delete=models.PROTECT, related_name="regras"
    )
    setores_alvo = models.ManyToManyField("organizacao.Setor", blank=True, related_name="+")
    perfis_alvo = models.ManyToManyField("contas.Perfil", blank=True, related_name="+")

    prioridade = models.IntegerField(default=0, help_text="Desempate: maior prioridade vence.")
    status = models.CharField(max_length=20, choices=StatusRegra.choices, default=StatusRegra.RASCUNHO)
    vigencia_inicio = models.DateField(null=True, blank=True)
    vigencia_fim = models.DateField(null=True, blank=True)
    versao = models.PositiveIntegerField(default=0)
    publicada_em = models.DateTimeField(null=True, blank=True)
    publicada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ["codigo"]
        verbose_name = "regra do motor"
        verbose_name_plural = "regras do motor"

    def __str__(self):
        return f"{self.codigo} — {self.titulo}"


class FonteRegra(models.Model):
    """Fundamento documental da regra. Só aparece para quem pode consultar o documento."""

    regra = models.ForeignKey(Regra, on_delete=models.CASCADE, related_name="fontes")
    documento = models.ForeignKey("documentos.Documento", on_delete=models.PROTECT, related_name="+")
    pagina = models.PositiveIntegerField(null=True, blank=True)
    secao = models.CharField(max_length=255, blank=True)
    trecho_citado = models.TextField(blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["regra", "ordem", "id"]


class VersaoRegra(models.Model):
    """Fotografia imutável de cada publicação, para rastrear qual versão respondeu."""

    regra = models.ForeignKey(Regra, on_delete=models.CASCADE, related_name="versoes")
    versao = models.PositiveIntegerField()
    conteudo = models.JSONField()
    publicada_em = models.DateTimeField(auto_now_add=True)
    publicada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        unique_together = [("regra", "versao")]
        ordering = ["regra", "-versao"]
