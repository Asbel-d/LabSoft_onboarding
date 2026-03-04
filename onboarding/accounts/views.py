from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponseForbidden
from django.db import transaction
from .models import Ingreso, IngresoCurso, IngresoAplicacion, CatalogoItem
from .forms import SeleccionCursosAppsForm

def es_rrhh(user):
    return user.groups.filter(name="RRHH").exists()

@login_required
def redireccion_por_rol(request):
    if es_rrhh(request.user):
        return redirect("panel_rrhh")
    if es_jefe_credito(request.user):
        return redirect("panel_jefe_credito")
    return HttpResponseForbidden("No tienes un rol autorizado para ingresar.")

@login_required
@user_passes_test(es_rrhh, login_url="/login/")
def panel_rrhh(request):
    return render(request, "accounts/panel_rrhh.html")

AREA_CREDITO = "Análisis de Crédito"   # EXACTO como lo insertaste en tu BD

def es_jefe_credito(user):
    return user.is_authenticated and user.groups.filter(name="JEFE_CREDITO").exists()

@login_required(login_url="/login/")
@user_passes_test(es_jefe_credito, login_url="/login/")
def panel_jefe_credito(request):
    ingresos = (
        Ingreso.objects
        .select_related("puesto_organizacional__area")
        .filter(puesto_organizacional__area__nombre=AREA_CREDITO)
        .order_by("-fecha_ingreso", "-id")
    )
    return render(request, "accounts/panel_jefe_credito.html", {"ingresos": ingresos, "area": AREA_CREDITO})

@login_required(login_url="/login/")
@user_passes_test(es_jefe_credito, login_url="/login/")
def jefe_credito_seleccionar(request, ingreso_id: int):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
        puesto_organizacional__area__nombre=AREA_CREDITO
    )

    cursos_actuales_ids = set(IngresoCurso.objects.filter(ingreso=ingreso).values_list("curso_id", flat=True))
    apps_actuales_ids = set(IngresoAplicacion.objects.filter(ingreso=ingreso).values_list("aplicacion_id", flat=True))

    if request.method == "POST":
        form = SeleccionCursosAppsForm(request.POST)
        if form.is_valid():
            cursos_sel = form.cleaned_data["cursos"]
            apps_sel = form.cleaned_data["aplicativos"]

            with transaction.atomic():
                # Reemplaza selección (simple y claro)
                IngresoCurso.objects.filter(ingreso=ingreso).delete()
                IngresoAplicacion.objects.filter(ingreso=ingreso).delete()

                IngresoCurso.objects.bulk_create([
                    IngresoCurso(ingreso=ingreso, curso=c) for c in cursos_sel
                ])
                IngresoAplicacion.objects.bulk_create([
                    IngresoAplicacion(ingreso=ingreso, aplicacion=a) for a in apps_sel
                ])

            return redirect("panel_jefe_credito")
    else:
        form = SeleccionCursosAppsForm(initial={
            "cursos": CatalogoItem.objects.filter(id__in=cursos_actuales_ids),
            "aplicativos": CatalogoItem.objects.filter(id__in=apps_actuales_ids),
        })

    return render(request, "accounts/jefe_credito_seleccionar.html", {"ingreso": ingreso, "form": form})