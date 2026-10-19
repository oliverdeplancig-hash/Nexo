"""Confere e ajusta uma instalação para uso real (ADR-019). Seguro para rodar várias vezes.

- recusa se NEXO_DEBUG estiver ligado ou a chave secreta for a padrão;
- desativa as contas de demonstração (senha pública Nexo@demo2026), se existirem;
- avisa sobre documentos de demonstração ainda no acervo.
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.contas.models import Usuario

CONTAS_DEMO = ["admin.demo", "servidor.demo", "ti.demo"]


class Command(BaseCommand):
    help = "Confere a configuração de produção e desativa contas de demonstração."

    def handle(self, *args, **opcoes):
        if settings.DEBUG:
            raise CommandError("NEXO_DEBUG está ligado. Em uso real, defina NEXO_DEBUG=false no .env.")
        if settings.SECRET_KEY.startswith("dev-inseguro") or len(settings.SECRET_KEY) < 40:
            raise CommandError("Defina NEXO_SECRET_KEY com uma chave longa e aleatória no .env.")
        desativadas = Usuario.objects.filter(username__in=CONTAS_DEMO, is_active=True).update(is_active=False)
        if desativadas:
            self.stdout.write(self.style.WARNING(f"{desativadas} conta(s) de demonstração desativada(s)."))
        from apps.documentos.models import Documento

        demo = Documento.objects.filter(descricao="Documento fictício de demonstração.").exclude(status="arquivado")
        if demo.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"Há {demo.count()} documento(s) fictício(s) de demonstração no acervo. Arquive-os na tela do documento."
                )
            )
        self.stdout.write(self.style.SUCCESS("Configuração de produção conferida."))
