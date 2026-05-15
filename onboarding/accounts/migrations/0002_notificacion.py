from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_cancelacion_observaciones"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE TABLE IF NOT EXISTS notificacion (
                    id serial PRIMARY KEY,
                    usuario_id integer NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
                    ingreso_id integer NULL REFERENCES ingreso(id) ON DELETE CASCADE,
                    titulo varchar(160) NOT NULL,
                    mensaje text NOT NULL,
                    url varchar(500) NOT NULL,
                    leida boolean NOT NULL DEFAULT false,
                    fecha_creacion timestamp with time zone NOT NULL DEFAULT now()
                );

                CREATE INDEX IF NOT EXISTS notificacion_usuario_leida_idx
                    ON notificacion (usuario_id, leida, fecha_creacion DESC);

                CREATE INDEX IF NOT EXISTS notificacion_ingreso_idx
                    ON notificacion (ingreso_id);
            """,
            reverse_sql="""
                DROP TABLE IF EXISTS notificacion;
            """,
        ),
    ]
