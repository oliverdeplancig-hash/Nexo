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
