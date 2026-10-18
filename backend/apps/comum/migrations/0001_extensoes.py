"""Extensões do PostgreSQL e configuração de busca textual em português.

Requer que o pacote do pgvector esteja instalado no servidor PostgreSQL
(ver docs/database/README.md). A criação das extensões exige privilégio
adequado; se o DBA preferir, execute o SQL manualmente antes do migrate.
"""

from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations
from pgvector.django import VectorExtension

CONFIGURACAO_FTS = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'nexo_pt') THEN
        CREATE TEXT SEARCH CONFIGURATION nexo_pt (COPY = portuguese);
        ALTER TEXT SEARCH CONFIGURATION nexo_pt
            ALTER MAPPING FOR hword, hword_part, word WITH unaccent, portuguese_stem;
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        VectorExtension(),
        UnaccentExtension(),
        migrations.RunSQL(CONFIGURACAO_FTS, reverse_sql="DROP TEXT SEARCH CONFIGURATION IF EXISTS nexo_pt;"),
    ]
