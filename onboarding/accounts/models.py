from django.db import models

class Usuario(models.Model):
    id = models.AutoField(primary_key=True)
    username = models.CharField(max_length=150)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=30)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "usuario"
    
    def __str__(self):
        return f"{self.username} ({self.role})"

class Area(models.Model):
    id = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=150)
    jefe_usuario = models.ForeignKey(
        Usuario,
        on_delete=models.DO_NOTHING,
        db_column="jefe_usuario_id",
        related_name="areas_a_cargo"
    )

    class Meta:
        managed = False
        db_table = "area"
    
    def __str__(self):
        return self.nombre


class PuestoOrganizacional(models.Model):
    id = models.AutoField(primary_key=True)
    nombre_puesto = models.CharField(max_length=150)
    area = models.ForeignKey(Area, on_delete=models.DO_NOTHING, db_column="area_id")

    class Meta:
        managed = False
        db_table = "puesto_organizacional"
    
    def __str__(self):
        return f"{self.nombre_puesto} - {self.area.nombre}"


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
    
    def __str__(self):
        return f"{self.codigo_proceso} - {self.nombre_empleado}"


class CatalogoItem(models.Model):
    id = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20)   # 'CURSO' | 'APLICACION' | 'DOTACION'
    nombre = models.CharField(max_length=200)

    class Meta:
        managed = False
        db_table = "catalogo_item"
    
    def __str__(self):
        return f"{self.nombre} ({self.tipo})"


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