"""Impede UPDATE e DELETE na trilha de auditoria diretamente no banco.

Expurgo por política de retenção, quando aprovado, deve ser feito por
procedimento documentado do DBA (desabilitando o gatilho de forma auditada).
"""

from django.db import migrations

SQL = """
CREATE OR REPLACE FUNCTION auditoria_somente_insercao() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'A trilha de auditoria do Nexo é somente-inserção.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auditoria_bloqueia_alteracao ON auditoria_eventoauditoria;
CREATE TRIGGER auditoria_bloqueia_alteracao
    BEFORE UPDATE OR DELETE ON auditoria_eventoauditoria
    FOR EACH ROW EXECUTE FUNCTION auditoria_somente_insercao();
"""

REVERSO = """
DROP TRIGGER IF EXISTS auditoria_bloqueia_alteracao ON auditoria_eventoauditoria;
DROP FUNCTION IF EXISTS auditoria_somente_insercao();
"""


class Migration(migrations.Migration):
    dependencies = [("auditoria", "0002_initial")]
    operations = [migrations.RunSQL(SQL, reverse_sql=REVERSO)]
