"""Mostra a saúde do sistema no terminal (ADR-023). Código de saída 1 se houver problema (útil em monitoramento).

python manage.py verificar_saude [--avisar]
"""

from django.core.management.base import BaseCommand

from apps.manutencao import saude

MARCA = {saude.OK: "OK      ", saude.ATENCAO: "ATENÇÃO ", saude.PROBLEMA: "PROBLEMA"}


class Command(BaseCommand):
    help = "Verifica banco, disco, cópias, processamento, IA, certificado e configuração."

    def add_arguments(self, parser):
        parser.add_argument("--avisar", action="store_true", help="Notifica os administradores dos problemas.")

    def handle(self, *args, avisar=False, **opcoes):
        resultado = saude.verificar()
        for item in resultado["itens"]:
            estilo = {saude.OK: self.style.SUCCESS, saude.ATENCAO: self.style.WARNING}.get(
                item["situacao"], self.style.ERROR
            )
            self.stdout.write(estilo(f"{MARCA[item['situacao']]} {item['titulo']}: {item['resumo']}"))
            if item["acao"]:
                self.stdout.write(f"         → {item['acao']}")
        if avisar:
            self.stdout.write(f"Notificações enviadas: {saude.avisar()}")
        if resultado["situacao"] == saude.PROBLEMA:
            raise SystemExit(1)
