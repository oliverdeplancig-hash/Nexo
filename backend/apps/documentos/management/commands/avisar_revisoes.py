from django.core.management.base import BaseCommand

from apps.documentos.vigencia import avisar_revisoes


class Command(BaseCommand):
    help = "Avisa quem mantém documentos com revisão próxima ou atrasada (ADR-015). Pode rodar várias vezes ao dia."

    def handle(self, *args, **opcoes):
        enviados = avisar_revisoes()
        self.stdout.write(f"Avisos de revisão enviados: {enviados}")
