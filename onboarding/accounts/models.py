from django.db import models

class Area(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    jefe_usuario_id = models.IntegerField()

    class Meta:
        managed = False
        db_table = "area"


class PuestoOrganizacional(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_puesto = models.CharField(max_length=150)
    area = models.ForeignKey(Area, on_delete=models.DO_NOTHING, db_column="area_id")

    class Meta:
        managed = False
        db_table = "puesto_organizacional"


class Ingreso(models.Model):
    id = models.AutoField(primary_key=True)
    codigo_proceso = models.CharField(max_length=50)
    nombre_empleado = models.CharField(max_length=200)
    tipo_documento = models.CharField(max_length=50)
    documento = models.CharField(max_length=50)
    fecha_ingreso = models.DateField()
    puesto_organizacional = models.ForeignKey(
        PuestoOrganizacional, on_delete=models.DO_NOTHING, db_column="puesto_organizacional_id"
    )
    estado = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = "ingreso"


class CatalogoItem(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20)   # 'CURSO' | 'APLICACION' | 'DOTACION'
    nombre = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = "catalogo_item"


class IngresoCurso(models.Model):
    id = models.AutoField(primary_key=True)
    ingreso = models.ForeignKey(Ingreso, on_delete=models.CASCADE, db_column="ingreso_id")
    curso = models.ForeignKey(CatalogoItem, on_delete=models.CASCADE, db_column="curso_id")

    class Meta:
        managed = False
        db_table = "ingreso_curso"


class IngresoAplicacion(models.Model):
    id = models.AutoField(primary_key=True)
    ingreso = models.ForeignKey(Ingreso, on_delete=models.CASCADE, db_column="ingreso_id")
    aplicacion = models.ForeignKey(CatalogoItem, on_delete=models.CASCADE, db_column="aplicacion_id")

    class Meta:
        managed = False
        db_table = "ingreso_aplicacion"