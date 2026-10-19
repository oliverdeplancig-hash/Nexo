"""Avalia a qualidade das respostas do assistente com um conjunto de perguntas de referência (ADR-025).

    python manage.py avaliar_respostas avaliacao/exemplo-demonstracao.json
    python manage.py avaliar_respostas avaliacao/local/ccp.json --saida avaliacao/local/resultados --minimo 0.8

Pergunta como o usuário indicado no conjunto (ou --usuario), respeitando as permissões dele. Mostra o resumo,
grava relatório em Markdown e JSON (com --saida) e termina com erro se a taxa de casos aprovados ficar abaixo
de --minimo.
"""

from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.contas.models import Usuario
from apps.conversas import avaliacao


class Command(BaseCommand):
    help = "Mede a qualidade das respostas do assistente com perguntas de referência."

    def add_arguments(self, parser):
        parser.add_argument("conjunto", help="Arquivo JSON do conjunto de avaliação.")
        parser.add_argument("--usuario", help="Login usado nas perguntas (padrão: o do conjunto).")
        parser.add_argument("--saida", help="Pasta para gravar o relatório (Markdown e JSON).")
        parser.add_argument("--minimo", type=float, default=0.0, help="Taxa mínima de casos aprovados (0 a 1).")
        parser.add_argument("--casos", nargs="*", help="Só estes ids.")

    def handle(self, *args, conjunto, usuario=None, saida=None, minimo=0.0, casos=None, **opcoes):
        try:
            dados, lista = avaliacao.carregar(conjunto)
        except (OSError, ValueError, TypeError) as erro:
            raise CommandError(f"Conjunto de avaliação inválido: {erro}") from erro
        if casos:
            lista = [c for c in lista if c.id in set(casos)]
        login = usuario or dados.get("usuario")
        pessoa = Usuario.objects.filter(username=login, is_active=True).first() if login else None
        if pessoa is None:
            raise CommandError("Informe um usuário ativo (--usuario ou campo 'usuario' do conjunto).")
        nome = dados.get("nome") or Path(conjunto).stem
        cfg = settings.NEXO_IA
        configuracao = {
            "conjunto": Path(conjunto).name,
            "usuário": login,
            "provedor de IA": cfg["PROVEDOR"],
            "modelo": cfg["MODELO_CHAT"] if cfg["PROVEDOR"] == "ollama" else "—",
            "embeddings": cfg["MODELO_EMBEDDING"] if cfg["PROVEDOR"] == "ollama" else "teste (hash)",
            "data": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }

        self.stdout.write(f"Avaliando {len(lista)} casos de '{nome}' como {login}…")
        resultados = []
        for caso in lista:
            r = avaliacao.avaliar_caso(pessoa, caso)
            resultados.append(r)
            marca = self.style.SUCCESS("ok    ") if r.aprovado else self.style.ERROR("FALHOU")
            self.stdout.write(f"  {marca} {r.id} [{r.origem}, {r.segundos} s] {caso.pergunta[:70]}")

        resumo = avaliacao.resumir(resultados)
        texto = avaliacao.relatorio_markdown(nome, configuracao, resumo, resultados)
        self.stdout.write("")
        self.stdout.write(texto.split("## Casos")[0])
        if saida:
            pasta = Path(saida)
            pasta.mkdir(parents=True, exist_ok=True)
            base = pasta / f"{Path(conjunto).stem}-{datetime.now():%Y%m%d-%H%M}"
            base.with_suffix(".md").write_text(texto, encoding="utf-8")
            base.with_suffix(".json").write_text(
                avaliacao.como_json(nome, configuracao, resumo, resultados), encoding="utf-8"
            )
            self.stdout.write(f"Relatório: {base.with_suffix('.md')}")
        taxa = resumo["aprovados"]["taxa"] or 0
        if taxa < minimo:
            raise CommandError(f"Taxa de aprovação {taxa:.0%} abaixo do mínimo de {minimo:.0%}.")
