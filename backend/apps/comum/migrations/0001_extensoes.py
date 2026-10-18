"""Extensões do PostgreSQL e configuração de busca textual em português.

- `vector` (pgvector) é obrigatória.
- `unaccent` é usada quando disponível (servidor da instituição). Em instalações
  locais sem ela (ex.: PostgreSQL embutido do pgserver no Windows), a configuração
  `nexo_pt` é criada sem unaccent e a busca consulta as duas grafias (com e sem acento).
"""

from django.db import migrations
from pgvector.django import VectorExtension

EXTENSOES_E_FTS = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'unaccent') THEN
        CREATE EXTENSION IF NOT EXISTS unaccent;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'nexo_pt') THEN
        CREATE TEXT SEARCH CONFIGURATION nexo_pt (COPY = portuguese);
        IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'unaccent') THEN
            ALTER TEXT SEARCH CONFIGURATION nexo_pt
                ALTER MAPPING FOR hword, hword_part, word WITH unaccent, portuguese_stem;
        END IF;
    END IF;
END
$$;
"""


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        VectorExtension(),
        migrations.RunSQL(EXTENSOES_E_FTS, reverse_sql="DROP TEXT SEARCH CONFIGURATION IF EXISTS nexo_pt;"),
    ]
