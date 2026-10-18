import hashlib
import json

from django.conf import settings
from django.db import models
from django.utils import timezone


class TipoEvento(models.TextChoices):
    LOGIN = "LOGIN", "Login"
    LOGOUT = "LOGOUT", "Encerramento de sessão"
    DOCUMENTO_ABERTO = "DOCUMENTO_ABERTO", "Abertura de documento"
    DOCUMENTO_VISUALIZADO = "DOCUMENTO_VISUALIZADO", "Visualização do arquivo"
    DOCUMENTO_BAIXADO = "DOCUMENTO_BAIXADO", "Download de documento"
    DOCUMENTO_INCLUIDO = "DOCUMENTO_INCLUIDO", "Inclusão de documento"
    DOCUMENTO_ALTERADO = "DOCUMENTO_ALTERADO", "Atualização de documento"
    DOCUMENTO_ARQUIVADO = "DOCUMENTO_ARQUIVADO", "Arquivamento de documento"
    DOCUMENTO_PROCESSADO = "DOCUMENTO_PROCESSADO", "Processamento de documento"
    PERMISSAO_CONCEDIDA = "PERMISSAO_CONCEDIDA", "Permissão concedida"
    PERMISSAO_REVOGADA = "PERMISSAO_REVOGADA", "Permissão revogada"
    CONSULTA_ASSISTENTE = "CONSULTA_ASSISTENTE", "Consulta ao assistente"
    BUSCA = "BUSCA", "Busca no repositório"
    FALHA_AUTORIZACAO = "FALHA_AUTORIZACAO", "Falha de autorização"
    ADMIN_USUARIO = "ADMIN_USUARIO", "Administração de usuários"
    ADMIN_PERMISSAO = "ADMIN_PERMISSAO", "Administração de perfis e permissões"
    ADMIN_SETOR = "ADMIN_SETOR", "Administração de setores"
    ADMIN_REGRA = "ADMIN_REGRA", "Administração de regras do motor"


class Resultado(models.TextChoices):
    SUCESSO = "SUCESSO", "Sucesso"
    FALHA = "FALHA", "Falha"
    NEGADO = "NEGADO", "Negado"


class EventoAuditoria(models.Model):
    """Trilha de auditoria somente-inserção, encadeada por hash.

    Cada evento guarda o hash do anterior; qualquer alteração ou remoção no
    meio da cadeia é detectada por `verificar_integridade`. A tabela também é
    protegida por gatilho no PostgreSQL contra UPDATE e DELETE.

    `detalhes` NUNCA contém conteúdo de documentos ou o texto das conversas.
    """

    ocorrido_em = models.DateTimeField(default=timezone.now, db_index=True)
    tipo = models.CharField(max_length=40, choices=TipoEvento.choices, db_index=True)
    resultado = models.CharField(max_length=10, choices=Resultado.choices, default=Resultado.SUCESSO)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT, related_name="+")
    usuario_login = models.CharField(max_length=150, blank=True)
    setor_sigla = models.CharField(max_length=30, blank=True, db_index=True)
    objeto_tipo = models.CharField(max_length=60, blank=True)
    objeto_id = models.CharField(max_length=60, blank=True)
    objeto_descricao = models.CharField(max_length=300, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    detalhes = models.JSONField(default=dict, blank=True)
    hash_anterior = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64, unique=True)

    class Meta:
        ordering = ["-id"]
        verbose_name = "evento de auditoria"
        verbose_name_plural = "eventos de auditoria"

    def conteudo_para_hash(self) -> str:
        return json.dumps(
            {
                "ocorrido_em": self.ocorrido_em.isoformat(),
                "tipo": self.tipo,
                "resultado": self.resultado,
                "usuario": self.usuario_id,
                "usuario_login": self.usuario_login,
                "setor": self.setor_sigla,
                "objeto": [self.objeto_tipo, self.objeto_id, self.objeto_descricao],
                "ip": self.ip,
                "detalhes": self.detalhes,
                "anterior": self.hash_anterior,
            },
            sort_keys=True,
            ensure_ascii=False,
            default=str,
        )

    def calcular_hash(self) -> str:
        return hashlib.sha256(self.conteudo_para_hash().encode("utf-8")).hexdigest()

    def save(self, *args, **kwargs):
        if self.pk:
            raise RuntimeError("Eventos de auditoria não podem ser alterados.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError("Eventos de auditoria não podem ser removidos.")
