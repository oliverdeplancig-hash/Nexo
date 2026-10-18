from django.core.management.base import BaseCommand

from apps.contas.models import Funcao, Perfil
from apps.documentos.models import Categoria

PERFIS_PADRAO = [
    ("servidor", "Servidor", "Consulta documentos autorizados e usa o assistente.", []),
    (
        "gestor-documental",
        "Gestor documental",
        "Cadastra documentos, organiza coleções e mantém as regras do motor determinístico.",
        [Funcao.IMPORTAR_DOCUMENTOS, Funcao.GERIR_COLECOES, Funcao.GERIR_REGRAS],
    ),
    (
        "administrador",
        "Administrador",
        "Administra usuários e o diretório de setores.",
        [Funcao.ADMIN_USUARIOS, Funcao.GERIR_SETORES],
    ),
    (
        "admin-permissoes",
        "Administrador de permissões",
        "Gerencia perfis e permissões críticas. Toda ação é auditada.",
        [Funcao.ADMIN_PERMISSOES, Funcao.ADMIN_USUARIOS],
    ),
    ("auditor", "Auditor", "Consulta a trilha de auditoria.", [Funcao.VER_AUDITORIA]),
]

CATEGORIAS_PADRAO = ["Norma", "Procedimento", "Manual", "Modelo", "Orientação", "Ato administrativo"]


class Command(BaseCommand):
    help = "Cria os perfis e categorias padrão do Nexo (idempotente)."

    def handle(self, *args, **opcoes):
        for codigo, nome, descricao, funcoes in PERFIS_PADRAO:
            perfil, criado = Perfil.objects.get_or_create(
                codigo=codigo, defaults={"nome": nome, "descricao": descricao, "funcoes": [str(f) for f in funcoes]}
            )
            self.stdout.write(f"{'criado' if criado else 'existente'}: perfil {perfil.codigo}")
        for nome in CATEGORIAS_PADRAO:
            Categoria.objects.get_or_create(nome=nome)
        self.stdout.write(self.style.SUCCESS("Perfis e categorias prontos."))
