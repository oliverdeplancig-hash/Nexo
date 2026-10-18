"""Recursos opcionais do PostgreSQL detectados em tempo de execução."""

from functools import lru_cache

from django.db import connection


@lru_cache(maxsize=1)
def tem_unaccent() -> bool:
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'unaccent'")
        return cursor.fetchone() is not None
