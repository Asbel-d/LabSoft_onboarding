from django.contrib import admin
from .models import Area, CatalogoItem, Ingreso, IngresoAplicacion, IngresoCurso, PuestoOrganizacional, Usuario


class AreaInline(admin.TabularInline):
    model = Area
    fk_name = "jefe_usuario"
    extra = 0
    fields = ("nombre",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jefe_usuario":
            kwargs["queryset"] = Usuario.objects.filter(role="JEFE").order_by("username")
            kwargs["empty_label"] = None
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "jefe_usuario":
            field.required = True
        return field

@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "username", "role", "is_active", "is_staff", "is_superuser")
    search_fields = ("username", "role")
    list_filter = ("role", "is_active", "is_staff", "is_superuser")
    inlines = (AreaInline,)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "jefe_usuario")
    list_editable = ("jefe_usuario",)
    list_select_related = ("jefe_usuario",)
    search_fields = ("nombre", "jefe_usuario__username")
    list_filter = ("jefe_usuario", "jefe_usuario__role")
    fields = ("nombre", "jefe_usuario")
    autocomplete_fields = ("jefe_usuario",)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "jefe_usuario":
            kwargs["queryset"] = Usuario.objects.filter(role="JEFE").order_by("username")
            kwargs["empty_label"] = None
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "jefe_usuario":
            field.required = True
        return field


@admin.register(PuestoOrganizacional)
class PuestoOrganizacionalAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre_puesto", "area")
    list_filter = ("area",)
    search_fields = ("nombre_puesto",)


@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo_proceso", "nombre_empleado", "puesto_organizacional", "fecha_ingreso", "estado")
    list_filter = ("estado", "puesto_organizacional__area")
    search_fields = ("codigo_proceso", "nombre_empleado", "documento")


@admin.register(CatalogoItem)
class CatalogoItemAdmin(admin.ModelAdmin):
    list_display = ("id", "tipo", "nombre")
    list_filter = ("tipo",)
    search_fields = ("nombre",)


@admin.register(IngresoCurso)
class IngresoCursoAdmin(admin.ModelAdmin):
    list_display = ("id", "ingreso", "curso")
    list_filter = ("curso",)


@admin.register(IngresoAplicacion)
class IngresoAplicacionAdmin(admin.ModelAdmin):
    list_display = ("id", "ingreso", "aplicacion")
    list_filter = ("aplicacion",)