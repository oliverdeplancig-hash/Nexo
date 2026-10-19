from django.conf import settings
from django.db import models


class Conversa(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversas")
    titulo = models.CharField(max_length=200, default="Nova conversa")
    documento_contexto = models.ForeignKey(
        "documentos.Documento",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        help_text="Quando informado, a IA só usa este documento (respeitando as permissões atuais).",
    )
    arquivada = models.BooleanField(default=False)
    # Memória por compactação (ADR-021): resumo determinístico das mensagens antigas desta conversa.
    memoria = models.JSONField(default=dict, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-atualizada_em"]

    def __str__(self):
        return self.titulo


class Origem(models.TextChoices):
    DETERMINISTICO = "deterministico", "Motor determinístico"
    RAG = "rag", "IA com fontes"
    EXTRATIVO = "extrativo", "Trechos (IA indisponível)"
    SEM_FONTES = "sem_fontes", "Sem fontes suficientes"
    DESAMBIGUACAO = "desambiguacao", "Desambiguação"
    ERRO = "erro", "Erro"


class Confianca(models.TextChoices):
    VERIFICADA = "verificada", "Resposta curada e aprovada"
    FUNDAMENTADA = "fundamentada", "Fundamentada em fontes citadas"
    CAUTELA = "cautela", "Confira com atenção"


class Mensagem(models.Model):
    class Papel(models.TextChoices):
        USUARIO = "usuario", "Usuário"
        ASSISTENTE = "assistente", "Assistente"

    conversa = models.ForeignKey(Conversa, on_delete=models.CASCADE, related_name="mensagens")
    papel = models.CharField(max_length=12, choices=Papel.choices)
    conteudo = models.TextField()
    origem = models.CharField(max_length=20, choices=Origem.choices, blank=True)
    confianca = models.CharField(max_length=20, choices=Confianca.choices, blank=True)
    etapas = models.JSONField(default=list, blank=True)
    setor = models.JSONField(null=True, blank=True)
    setores_sugeridos = models.JSONField(default=list, blank=True)
    sugestoes = models.JSONField(default=list, blank=True)
    fontes = models.JSONField(default=list, blank=True)
    rastro = models.JSONField(default=dict, blank=True)
    interrompida = models.BooleanField(default=False)
    duracao_ms = models.PositiveIntegerField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["conversa", "id"]


class MotivoAvaliacao(models.TextChoices):
    INCORRETA = "incorreta", "Informação incorreta"
    INCOMPLETA = "incompleta", "Incompleta"
    NAO_RESPONDEU = "nao_respondeu", "Não respondeu à pergunta"
    DESATUALIZADA = "desatualizada", "Desatualizada"
    SETOR_ERRADO = "setor_errado", "Setor indicado errado"
    OUTRO = "outro", "Outro"


class AvaliacaoResposta(models.Model):
    """Avaliação de uma resposta pelo próprio autor da pergunta (útil / não útil)."""

    mensagem = models.OneToOneField(Mensagem, on_delete=models.CASCADE, related_name="avaliacao")
    util = models.BooleanField()
    motivo = models.CharField(max_length=20, choices=MotivoAvaliacao.choices, blank=True)
    comentario = models.CharField(max_length=500, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "avaliação de resposta"
        verbose_name_plural = "avaliações de respostas"


class TratamentoLacuna(models.Model):
    """Registro de que uma lacuna (pergunta mal respondida) foi analisada pela gestão do motor."""

    mensagem = models.OneToOneField(Mensagem, on_delete=models.CASCADE, related_name="tratamento")
    tratada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    tratada_em = models.DateTimeField(auto_now_add=True)
    observacao = models.CharField(max_length=500, blank=True)
    regra = models.ForeignKey("motor.Regra", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")

    class Meta:
        verbose_name = "tratamento de lacuna"
        verbose_name_plural = "tratamentos de lacunas"
