from django.db import migrations


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE ingreso
                ADD COLUMN IF NOT EXISTS observacion_cancelacion text;

                ALTER TABLE ingreso
                ADD COLUMN IF NOT EXISTS fecha_cancelacion timestamp with time zone;
            """,
            reverse_sql="""
                ALTER TABLE ingreso
                DROP COLUMN IF EXISTS observacion_cancelacion;

                ALTER TABLE ingreso
                DROP COLUMN IF EXISTS fecha_cancelacion;
            """,
        ),
    ]
