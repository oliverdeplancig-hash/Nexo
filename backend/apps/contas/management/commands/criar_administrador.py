"""Cria o primeiro administrador do Nexo com senha temporária gerada (ADR-018/ADR-019).

    python manage.py criar_administrador --usuario fulano --nome "Fulano de Tal" --email fulano@...

A senha temporária aparece uma única vez (e vai por e-mail, se configurado); no primeiro acesso a pessoa
cria a própria senha.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.contas import credenciais
from apps.contas.models import Perfil, Usuario

PERFIS_DO_ADMINISTRADOR = ["servidor", "gestor-documental", "administrador", "admin-permissoes", "auditor"]


class Command(BaseCommand):
    help = "Cria um administrador com todos os perfis e senha temporária gerada."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True)
        parser.add_argument("--nome", default="")
        parser.add_argument("--email", default="")
        parser.add_argument("--nova-senha", action="store_true", help="Se já existir, gera nova senha temporária.")

    @transaction.atomic
    def handle(self, *args, usuario, nome, email, nova_senha=False, **opcoes):
        from django.core.management import call_command

        call_command("inicializar_nexo", verbosity=0)
        existente = Usuario.objects.filter(username=usuario).first()
        if existente and not nova_senha:
            raise CommandError(f"O usuário {usuario} já existe. Use --nova-senha para gerar outra senha temporária.")
        conta = existente or Usuario(username=usuario, nome_exibicao=nome, email=email)
        conta.is_active = True
        conta.save()
        conta.perfis.add(*Perfil.objects.filter(codigo__in=PERFIS_DO_ADMINISTRADOR))
        c = credenciais.emitir(conta, None, "administrador_inicial" if not existente else "redefinicao")
        self.stdout.write(self.style.SUCCESS(f"Administrador pronto: {c.usuario}"))
        self.stdout.write(f"Senha temporária (aparece só agora): {c.senha_temporaria}")
        if c.enviado_por_email:
            self.stdout.write(f"Também enviada para {c.destino_email}.")
        self.stdout.write("No primeiro acesso será pedida a criação de uma senha própria.")
