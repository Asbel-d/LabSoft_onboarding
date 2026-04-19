from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Count
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from difflib import SequenceMatcher
import unicodedata

from .forms import IngresoForm, SeleccionAplicativosForm, SeleccionCursosAppsForm
from .models import (
    Area,
    AsignacionPuestoFisico,
    CatalogoItem,
    Ingreso,
    IngresoAplicacion,
    IngresoCurso,
    IngresoDotacion,
    PuestoFisico,
    PuestoOrganizacional,
    RequerimientoJefe,
    Usuario,
)


SUGGESTION_RULES = [
    {
        "keywords": ["credito", "finanza", "financ", "cartera", "riesgo", "cobranza", "analisis de credito"],
        "cursos": [
            "Análisis de Capacidad de Pago",
            "Evaluación de Garantías Reales",
            "Gestión de Cobranza Preventiva",
            "Gestión de Riesgo Operativo",
            "Excel Avanzado para Finanzas",
            "Actualización en Normas NIIF",
            "Inducción a la Cultura Cooperativa",
        ],
        "aplicativos": [
            "Core Financiero",
            "Banca Virtual",
            "App Móvil",
        ],
    },
    {
        "keywords": ["rrhh", "talento humano", "human", "persona", "personal", "bienestar"],
        "cursos": [
            "Comunicación Asertiva",
            "Brigadas de Primeros Auxilios",
            "Inducción a la Cultura Cooperativa",
            "Gestión de PQRS Eficiente",
        ],
        "aplicativos": [
            "App Móvil",
        ],
    },
    {
        "keywords": ["operacion", "operativo", "compras", "proveedor", "logistica", "servicio"],
        "cursos": [
            "Gestión de Compras y Proveedores",
            "Gestión de PQRS Eficiente",
            "Ciberseguridad para No Técnicos",
            "Comunicación Asertiva",
        ],
        "aplicativos": [
            "App Móvil",
            "Core Financiero",
        ],
    },
    {
        "keywords": ["tecnologia", "sistemas", "informacion", "ciber", "seguridad", "it"],
        "cursos": [
            "Ciberseguridad para No Técnicos",
            "Actualización en Normas NIIF",
            "Gestión de Riesgo Operativo",
        ],
        "aplicativos": [
            "App Móvil",
            "Core Financiero",
        ],
    },
    {
        "keywords": ["riesgo", "cumplimiento", "auditoria", "auditor", "control"],
        "cursos": [
            "Gestión de Riesgo Operativo",
            "Actualización en Normas NIIF",
            "Evaluación de Garantías Reales",
            "Análisis de Capacidad de Pago",
        ],
        "aplicativos": [
            "Core Financiero",
        ],
    },
]

DEFAULT_DOTACION_ITEMS = [
    "Uniforme corporativo",
    "Carné institucional",
    "Elementos de escritorio",
]


def _ensure_default_dotacion_items():
    for nombre in DEFAULT_DOTACION_ITEMS:
        CatalogoItem.objects.get_or_create(tipo="DOTACION", nombre=nombre)


def _ensure_default_office_seats():
    for number in range(1, 11):
        PuestoFisico.objects.get_or_create(
            codigo_puesto=f"OFICINA-{number:02d}",
            defaults={"estado": "DISPONIBLE"},
        )


def _office_seats_for_ingreso(ingreso):
    _ensure_default_office_seats()
    current_assignment = (
        AsignacionPuestoFisico.objects
        .filter(ingreso=ingreso)
        .select_related("puesto_fisico")
        .first()
    )
    current_seat_id = current_assignment.puesto_fisico_id if current_assignment else None
    occupied_by_others = set(
        AsignacionPuestoFisico.objects
        .exclude(ingreso=ingreso)
        .values_list("puesto_fisico_id", flat=True)
    )

    seats = []
    for puesto in PuestoFisico.objects.filter(codigo_puesto__startswith="OFICINA-").order_by("codigo_puesto")[:10]:
        is_current = puesto.id == current_seat_id
        is_occupied = puesto.id in occupied_by_others or (puesto.estado == "OCUPADO" and not is_current)
        seats.append({
            "id": puesto.id,
            "codigo": puesto.codigo_puesto,
            "estado": "OCUPADO" if is_occupied else "DISPONIBLE",
            "ocupado": is_occupied,
            "seleccionado": is_current,
        })
    return seats


def _normalize_text(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return text.lower()


def _score_catalog_items(candidates, keywords, limit=4):
    scored = []
    normalized_keywords = [_normalize_text(keyword) for keyword in keywords]

    for item in candidates:
        item_name = _normalize_text(item.nombre)
        score = 0.0

        for keyword in normalized_keywords:
            if keyword in item_name:
                score += 4.0
            else:
                score += SequenceMatcher(None, keyword, item_name).ratio()

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda pair: (-pair[0], pair[1].nombre))
    return [item for _, item in scored[:limit]]


def _merge_unique_items(primary, secondary, limit):
    seen = set()
    merged = []

    for item in list(primary) + list(secondary):
        if item.id in seen:
            continue
        seen.add(item.id)
        merged.append(item)
        if len(merged) >= limit:
            break

    return merged


def _historical_area_items(area_id, item_type, limit=4):
    if not area_id:
        return []

    if item_type == "CURSO":
        rows = (
            IngresoCurso.objects
            .filter(ingreso__puesto_organizacional__area_id=area_id)
            .values("curso_id")
            .annotate(total=Count("id"))
            .order_by("-total", "curso_id")[:limit]
        )
        ids = [row["curso_id"] for row in rows]
    else:
        rows = (
            IngresoAplicacion.objects
            .filter(ingreso__puesto_organizacional__area_id=area_id)
            .values("aplicacion_id")
            .annotate(total=Count("id"))
            .order_by("-total", "aplicacion_id")[:limit]
        )
        ids = [row["aplicacion_id"] for row in rows]

    if not ids:
        return []

    items_by_id = {
        item.id: item
        for item in CatalogoItem.objects.filter(id__in=ids, tipo=item_type)
    }
    return [items_by_id[item_id] for item_id in ids if item_id in items_by_id]


def _build_ai_suggestions(area_name="", puesto_name="", area_id=None):
    area_text = f"{area_name} {puesto_name}".strip()
    normalized_text = _normalize_text(area_text)

    catalogo = list(CatalogoItem.objects.all().order_by("tipo", "nombre"))
    cursos = [item for item in catalogo if item.tipo == "CURSO"]
    aplicativos = [item for item in catalogo if item.tipo == "APLICACION"]

    selected_rule = None
    for rule in SUGGESTION_RULES:
        if any(keyword in normalized_text for keyword in rule["keywords"]):
            selected_rule = rule
            break

    historical_cursos = _historical_area_items(area_id, "CURSO", limit=4)
    historical_apps = _historical_area_items(area_id, "APLICACION", limit=3)

    if selected_rule:
        rule_cursos = _score_catalog_items(cursos, selected_rule["cursos"], limit=4)
        rule_apps = _score_catalog_items(aplicativos, selected_rule["aplicativos"], limit=3)
    else:
        fallback_keywords = [word for word in normalized_text.split() if len(word) > 3]
        rule_cursos = _score_catalog_items(cursos, fallback_keywords or [area_text], limit=4)
        rule_apps = _score_catalog_items(aplicativos, fallback_keywords or [area_text], limit=3)

    suggested_cursos = _merge_unique_items(historical_cursos, rule_cursos, limit=4)
    suggested_apps = _merge_unique_items(historical_apps, rule_apps, limit=3)

    return {
        "label": area_text or "Área no identificada",
        "cursos": [{"id": item.id, "nombre": item.nombre} for item in suggested_cursos],
        "aplicativos": [{"id": item.id, "nombre": item.nombre} for item in suggested_apps],
    }


def _sync_ingreso_states():
    # Sincronización conservadora para datos legacy.
    # El avance principal del flujo se hace por acciones explícitas de cada panel.
    ingresos = Ingreso.objects.exclude(estado="CANCELADO")
    for ingreso in ingresos:
        has_cursos = IngresoCurso.objects.filter(ingreso=ingreso).exists()
        has_apps = IngresoAplicacion.objects.filter(ingreso=ingreso).exists()

        nuevo_estado = ingreso.estado
        if has_cursos and has_apps and ingreso.estado in ["CREADO_RRHH", "PENDIENTE_JEFE"]:
            nuevo_estado = "EN_EJECUCION"
        elif (not has_cursos or not has_apps) and ingreso.estado == "EN_EJECUCION":
            nuevo_estado = "PENDIENTE_JEFE"

        if nuevo_estado != ingreso.estado:
            ingreso.estado = nuevo_estado
            ingreso.save(update_fields=["estado"])

def es_rrhh(user):
    return user.groups.filter(name="RRHH").exists()

@login_required
def redireccion_por_rol(request):
    if request.user.is_superuser:
        return redirect("/admin/")
    if getattr(request.user, "role", None) == "ROOT":
        return redirect("/admin/")
    if es_rrhh(request.user):
        return redirect("panel_rrhh")
    if es_tecnologia(request.user):
        return redirect("panel_tecnologia")
    if es_talento_humano(request.user):
        return redirect("panel_talento_humano")
    if es_servicios(request.user):
        return redirect("panel_servicios")
    if es_jefe(request.user):
        return redirect("panel_jefe")
    return HttpResponseForbidden("No tienes un rol autorizado para ingresar.")

@login_required
@user_passes_test(es_rrhh, login_url="/login/")
def panel_rrhh(request):
    _sync_ingreso_states()
    ingresos = Ingreso.objects.all()
    return render(request, "accounts/panel_rrhh.html", {
        "total_ingresos": ingresos.count(),
        "pendientes_jefe": ingresos.filter(estado="PENDIENTE_JEFE").count(),
        "en_ejecucion": ingresos.filter(estado="EN_EJECUCION").count(),
        "finalizados": ingresos.filter(estado="FINALIZADO").count(),
    })

def es_jefe(user):
    return user.is_authenticated and user.groups.filter(name="JEFE").exists()


def es_tecnologia(user):
    return user.is_authenticated and user.groups.filter(name="TECNOLOGIA").exists()


def es_talento_humano(user):
    return user.is_authenticated and user.groups.filter(name="TALENTO_HUMANO").exists()


def es_servicios(user):
    return user.is_authenticated and user.groups.filter(name__in=["SERVICIOS", "Servicio generales"]).exists()


def _get_business_user_id(auth_user):
    business_user = Usuario.objects.filter(username=auth_user.username).only("id").first()
    if business_user:
        return business_user.id
    return auth_user.id

@login_required(login_url="/login/")
@user_passes_test(es_jefe, login_url="/login/")
def panel_jefe(request):
    _sync_ingreso_states()
    business_user_id = _get_business_user_id(request.user)
    areas_a_cargo = list(
        Area.objects.filter(jefe_usuario_id=business_user_id).order_by("nombre")
    )

    ingresos_area = (
        Ingreso.objects
        .select_related("puesto_organizacional__area")
        .filter(puesto_organizacional__area__jefe_usuario_id=business_user_id)
        .order_by("-fecha_ingreso", "-id")
    )
    ingresos_pendientes = ingresos_area.filter(estado__in=["CREADO_RRHH", "PENDIENTE_JEFE"])

    area_nombres = [area.nombre for area in areas_a_cargo]

    return render(request, "accounts/panel_jefe.html", {
        "ingresos": ingresos_pendientes,
        "areas": area_nombres,
        "areas_texto": ", ".join(area_nombres) if area_nombres else "Sin áreas asignadas",
        "total_ingresos": ingresos_area.count(),
        "pendientes_jefe": ingresos_pendientes.count(),
        "en_ejecucion": ingresos_area.filter(estado="EN_EJECUCION").count(),
    })

@login_required(login_url="/login/")
@user_passes_test(es_jefe, login_url="/login/")
def jefe_seleccionar(request, ingreso_id: int):
    _ensure_default_dotacion_items()
    business_user_id = _get_business_user_id(request.user)
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
        puesto_organizacional__area__jefe_usuario_id=business_user_id
    )

    cursos_actuales_ids = set(IngresoCurso.objects.filter(ingreso=ingreso).values_list("curso_id", flat=True))
    apps_actuales_ids = set(IngresoAplicacion.objects.filter(ingreso=ingreso).values_list("aplicacion_id", flat=True))
    dotaciones_actuales_ids = set(IngresoDotacion.objects.filter(ingreso=ingreso).values_list("dotacion_id", flat=True))
    requerimiento_actual = RequerimientoJefe.objects.filter(ingreso=ingreso).first()

    if request.method == "POST":
        form = SeleccionCursosAppsForm(request.POST)
        if form.is_valid():
            cursos_sel = form.cleaned_data["cursos"]
            apps_sel = form.cleaned_data["aplicativos"]
            dotaciones_sel = form.cleaned_data["dotaciones"]
            requiere_puesto = form.cleaned_data["requiere_puesto_trabajo"]

            with transaction.atomic():
                IngresoCurso.objects.filter(ingreso=ingreso).delete()
                IngresoAplicacion.objects.filter(ingreso=ingreso).delete()
                IngresoDotacion.objects.filter(ingreso=ingreso).delete()

                IngresoCurso.objects.bulk_create([
                    IngresoCurso(ingreso=ingreso, curso=c) for c in cursos_sel
                ])
                IngresoAplicacion.objects.bulk_create([
                    IngresoAplicacion(ingreso=ingreso, aplicacion=a) for a in apps_sel
                ])
                for dotacion in dotaciones_sel:
                    IngresoDotacion.objects.create(
                        ingreso=ingreso,
                        dotacion=dotacion,
                        estado_entrega="PENDIENTE",
                    )

                if requiere_puesto:
                    RequerimientoJefe.objects.update_or_create(
                        ingreso=ingreso,
                        defaults={
                            "equipo": form.cleaned_data["equipo"],
                            "sistema_operativo": form.cleaned_data["sistema_operativo"],
                            "fecha_definicion": timezone.now(),
                        }
                    )
                else:
                    RequerimientoJefe.objects.filter(ingreso=ingreso).delete()

                # El jefe define cursos y aplicativos para pasar a ejecución.
                if cursos_sel.exists() and apps_sel.exists():
                    ingreso.estado = "EN_EJECUCION"
                else:
                    ingreso.estado = "PENDIENTE_JEFE"
                ingreso.save(update_fields=["estado"])

            return redirect("panel_jefe")
    else:
        form = SeleccionCursosAppsForm(initial={
            "cursos": CatalogoItem.objects.filter(id__in=cursos_actuales_ids),
            "aplicativos": CatalogoItem.objects.filter(id__in=apps_actuales_ids),
            "dotaciones": CatalogoItem.objects.filter(id__in=dotaciones_actuales_ids),
            "requiere_puesto_trabajo": bool(requerimiento_actual),
            "equipo": requerimiento_actual.equipo if requerimiento_actual else "",
            "sistema_operativo": requerimiento_actual.sistema_operativo if requerimiento_actual else "",
        })

    sugerencias = _build_ai_suggestions(
        ingreso.puesto_organizacional.area.nombre,
        ingreso.puesto_organizacional.nombre_puesto,
        ingreso.puesto_organizacional.area_id,
    )

    return render(request, "accounts/jefe_seleccionar.html", {
        "ingreso": ingreso,
        "form": form,
        "sugeridos_cursos": sugerencias["cursos"],
        "sugeridos_aplicativos": sugerencias["aplicativos"],
        "sugeridos_cursos_ids": [item["id"] for item in sugerencias["cursos"]],
        "sugeridos_aplicativos_ids": [item["id"] for item in sugerencias["aplicativos"]],
    })

@login_required
def puesto_info(request, puesto_id):
    puesto = (PuestoOrganizacional.objects
              .select_related("area__jefe_usuario")  
              .get(id=puesto_id))

    jefe = puesto.area.jefe_usuario  # Usuario relacionado
    return JsonResponse({
        "area_id": puesto.area.id,
        "area_nombre": puesto.area.nombre,
        "sugerencias": _build_ai_suggestions(puesto.area.nombre, puesto.nombre_puesto, puesto.area_id),
        "jefe_id": jefe.id if jefe else None,
        "jefe_username": jefe.username if jefe else None,
    })

@login_required
def rrhh_ingreso_crear(request):
    if request.method == "POST":
        form = IngresoForm(request.POST)
        if form.is_valid():
            ingreso = form.save(commit=False)

            ingreso.estado = "CREADO_RRHH"
            ingreso.save()
            return redirect("rrhh_ingresos_listar")
    else:
        form = IngresoForm()

    return render(request, "accounts/ingreso_form.html", {"form": form, "modo": "crear"})

@login_required
def rrhh_ingreso_editar(request, ingreso_id):
    ingreso = get_object_or_404(Ingreso, id=ingreso_id)

    if request.method == "POST":
        form = IngresoForm(request.POST, instance=ingreso, allow_past_date=True)
        if form.is_valid():
            ingreso = form.save(commit=False)

            ingreso.save()
            return redirect("rrhh_ingresos_listar")
    else:
        form = IngresoForm(instance=ingreso, allow_past_date=True)

    return render(request, "accounts/ingreso_form.html", {"form": form, "modo": "editar", "ingreso": ingreso})


@login_required
def rrhh_ingresos_listar(request):
    _sync_ingreso_states()
    area_id = request.GET.get("area")
    estado = request.GET.get("estado")

    ingresos = Ingreso.objects.select_related("puesto_organizacional__area")

    if area_id:
        ingresos = ingresos.filter(puesto_organizacional__area_id=area_id)
    if estado:
        ingresos = ingresos.filter(estado=estado)

    areas = Area.objects.all().order_by("nombre")

    return render(
        request,
        "accounts/ingresos_list.html",
        {
            "ingresos": ingresos,
            "areas": areas,
            "area_id": area_id,
            "estado": estado,
        }
    )


@login_required
@user_passes_test(es_rrhh, login_url="/login/")
def rrhh_asignar_cursos(request, ingreso_id):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
    )
    cursos = IngresoCurso.objects.filter(ingreso=ingreso).select_related("curso").order_by("curso__nombre")
    has_cursos = cursos.exists()
    has_apps = IngresoAplicacion.objects.filter(ingreso=ingreso).exists()
    has_puesto_fisico = bool(ingreso.puesto_organizacional_id)

    if request.method == "POST":
        # RRHH/Talento confirma cursos; no finaliza proceso aquí.
        if has_cursos:
            ingreso.estado = "TALENTO_HUMANO_COMPLETADO"
        else:
            ingreso.estado = "PENDIENTE_JEFE"

        ingreso.save(update_fields=["estado"])
        return redirect("rrhh_ingresos_listar")

    return render(request, "accounts/rrhh_asignar_cursos.html", {
        "ingreso": ingreso,
        "cursos": cursos,
        "has_cursos": has_cursos,
        "has_apps": has_apps,
        "has_puesto_fisico": has_puesto_fisico,
    })


@login_required(login_url="/login/")
@user_passes_test(es_tecnologia, login_url="/login/")
def panel_tecnologia(request):
    _sync_ingreso_states()
    ingresos = (
        Ingreso.objects
        .select_related("puesto_organizacional__area")
        .filter(estado__in=["EN_EJECUCION", "TALENTO_HUMANO_COMPLETADO"])
        .filter(ingresoaplicacion__isnull=False)
        .distinct()
        .order_by("-fecha_ingreso", "-id")
    )

    return render(request, "accounts/panel_tecnologia.html", {
        "ingresos": ingresos,
        "pendientes_instalacion": ingresos.count(),
    })


@login_required(login_url="/login/")
@user_passes_test(es_tecnologia, login_url="/login/")
def tecnologia_asignar_aplicativos(request, ingreso_id):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
        estado__in=["EN_EJECUCION", "TALENTO_HUMANO_COMPLETADO"],
    )
    aplicativos = IngresoAplicacion.objects.filter(ingreso=ingreso).select_related("aplicacion").order_by("aplicacion__nombre")
    cursos = IngresoCurso.objects.filter(ingreso=ingreso).select_related("curso").order_by("curso__nombre")

    if request.method == "POST":
        has_apps = aplicativos.exists()
        if has_apps:
            ingreso.estado = "TECNOLOGIA_COMPLETADO"
            ingreso.save(update_fields=["estado"])
        return redirect("panel_tecnologia")

    return render(request, "accounts/tecnologia_asignar_aplicativos.html", {
        "ingreso": ingreso,
        "cursos": cursos,
        "aplicativos": aplicativos,
    })


@login_required(login_url="/login/")
@user_passes_test(es_talento_humano, login_url="/login/")
def panel_talento_humano(request):
    _sync_ingreso_states()
    ingresos = (
        Ingreso.objects
        .select_related("puesto_organizacional__area")
        .filter(estado__in=["EN_EJECUCION", "TECNOLOGIA_COMPLETADO"])
        .filter(ingresocurso__isnull=False)
        .distinct()
        .order_by("-fecha_ingreso", "-id")
    )
    return render(request, "accounts/panel_talento_humano.html", {
        "ingresos": ingresos,
        "pendientes": ingresos.count(),
    })


@login_required(login_url="/login/")
@user_passes_test(es_talento_humano, login_url="/login/")
def talento_confirmar_cursos(request, ingreso_id):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
        estado__in=["EN_EJECUCION", "TECNOLOGIA_COMPLETADO"],
    )
    cursos = IngresoCurso.objects.filter(ingreso=ingreso).select_related("curso").order_by("curso__nombre")

    if request.method == "POST":
        if cursos.exists():
            if ingreso.estado != "TECNOLOGIA_COMPLETADO":
                ingreso.estado = "TALENTO_HUMANO_COMPLETADO"
            ingreso.save(update_fields=["estado"])
        return redirect("panel_talento_humano")

    return render(request, "accounts/talento_confirmar_cursos.html", {
        "ingreso": ingreso,
        "cursos": cursos,
    })


@login_required(login_url="/login/")
@user_passes_test(es_servicios, login_url="/login/")
def panel_servicios(request):
    ingresos = (
        Ingreso.objects
        .select_related("puesto_organizacional__area")
        .filter(estado__in=["EN_EJECUCION", "TALENTO_HUMANO_COMPLETADO", "TECNOLOGIA_COMPLETADO"])
        .distinct()
        .order_by("-fecha_ingreso", "-id")
    )
    ingresos = ingresos.filter(
        ingresodotacion__isnull=False
    ) | ingresos.filter(
        requerimientojefe__isnull=False
    )
    ingresos = ingresos.distinct().order_by("-fecha_ingreso", "-id")
    return render(request, "accounts/panel_servicios.html", {
        "ingresos": ingresos,
        "pendientes": ingresos.count(),
    })


@login_required(login_url="/login/")
@user_passes_test(es_servicios, login_url="/login/")
def servicios_finalizar_ingreso(request, ingreso_id):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
        estado__in=["EN_EJECUCION", "TALENTO_HUMANO_COMPLETADO", "TECNOLOGIA_COMPLETADO"],
    )
    cursos = IngresoCurso.objects.filter(ingreso=ingreso).exists()
    apps = IngresoAplicacion.objects.filter(ingreso=ingreso).exists()
    dotaciones = IngresoDotacion.objects.filter(ingreso=ingreso).select_related("dotacion").order_by("dotacion__nombre")
    requerimiento = RequerimientoJefe.objects.filter(ingreso=ingreso).first()
    asignacion_puesto = AsignacionPuestoFisico.objects.filter(ingreso=ingreso).select_related("puesto_fisico").first()
    puestos_oficina = _office_seats_for_ingreso(ingreso) if requerimiento else []

    if request.method == "POST":
        dotaciones_entregadas_ids = request.POST.getlist("dotaciones_entregadas")
        puesto_fisico_id = request.POST.get("puesto_fisico_id")

        with transaction.atomic():
            for dotacion in dotaciones:
                dotacion.estado_entrega = "ENTREGADA" if str(dotacion.id) in dotaciones_entregadas_ids else "PENDIENTE"
                dotacion.save(update_fields=["estado_entrega"])

            puesto_ok = True
            if requerimiento:
                puesto_ok = False
                puesto_fisico = (
                    PuestoFisico.objects
                    .filter(id=puesto_fisico_id, codigo_puesto__startswith="OFICINA-")
                    .first()
                )
                ocupado_por_otro = (
                    puesto_fisico and
                    AsignacionPuestoFisico.objects
                    .filter(puesto_fisico=puesto_fisico)
                    .exclude(ingreso=ingreso)
                    .exists()
                )
                if puesto_fisico and not ocupado_por_otro:
                    if asignacion_puesto and asignacion_puesto.puesto_fisico_id != puesto_fisico.id:
                        puesto_anterior = asignacion_puesto.puesto_fisico
                        puesto_anterior.estado = "DISPONIBLE"
                        puesto_anterior.save(update_fields=["estado"])

                    puesto_fisico.estado = "OCUPADO"
                    puesto_fisico.save(update_fields=["estado"])
                    AsignacionPuestoFisico.objects.update_or_create(
                        ingreso=ingreso,
                        defaults={
                            "puesto_fisico": puesto_fisico,
                            "estado": "COMPLETADA",
                            "fecha_asignacion": timezone.now(),
                        }
                    )
                    puesto_ok = True

            dotacion_ok = not dotaciones.exists() or not dotaciones.exclude(estado_entrega="ENTREGADA").exists()

        if ingreso.estado == "TECNOLOGIA_COMPLETADO" and cursos and apps and puesto_ok and dotacion_ok:
            ingreso.estado = "FINALIZADO"
            ingreso.save(update_fields=["estado"])
            return redirect(f"/rrhh/ingresos/{ingreso.id}/acta-final/?volver=servicios")

        return redirect("servicios_finalizar_ingreso", ingreso_id=ingreso.id)

    return render(request, "accounts/servicios_finalizar_ingreso.html", {
        "ingreso": ingreso,
        "has_cursos": cursos,
        "has_apps": apps,
        "dotaciones": dotaciones,
        "requerimiento": requerimiento,
        "asignacion_puesto": asignacion_puesto,
        "puestos_oficina": puestos_oficina,
    })


@login_required
def rrhh_acta_final(request, ingreso_id):
    ingreso = get_object_or_404(
        Ingreso.objects.select_related("puesto_organizacional__area"),
        id=ingreso_id,
    )
    cursos = IngresoCurso.objects.filter(ingreso=ingreso).select_related("curso").order_by("curso__nombre")
    aplicativos = IngresoAplicacion.objects.filter(ingreso=ingreso).select_related("aplicacion").order_by("aplicacion__nombre")
    dotaciones = IngresoDotacion.objects.filter(ingreso=ingreso).select_related("dotacion").order_by("dotacion__nombre")
    requerimiento = RequerimientoJefe.objects.filter(ingreso=ingreso).first()
    asignacion_puesto = AsignacionPuestoFisico.objects.filter(ingreso=ingreso).select_related("puesto_fisico").first()

    solicitudes_pedidas = []
    solicitudes_respondidas = []

    for curso in cursos:
        solicitudes_pedidas.append(f"Curso: {curso.curso.nombre}")
        if ingreso.estado in ["TALENTO_HUMANO_COMPLETADO", "TECNOLOGIA_COMPLETADO", "FINALIZADO"]:
            solicitudes_respondidas.append(f"Curso completado: {curso.curso.nombre}")

    for aplicativo in aplicativos:
        solicitudes_pedidas.append(f"Aplicativo: {aplicativo.aplicacion.nombre}")
        if ingreso.estado in ["TECNOLOGIA_COMPLETADO", "FINALIZADO"]:
            solicitudes_respondidas.append(f"Aplicativo asignado: {aplicativo.aplicacion.nombre}")

    for dotacion in dotaciones:
        solicitudes_pedidas.append(f"Dotación/uniforme: {dotacion.dotacion.nombre}")
        if dotacion.estado_entrega == "ENTREGADA":
            solicitudes_respondidas.append(f"Dotación entregada: {dotacion.dotacion.nombre}")

    if requerimiento:
        solicitudes_pedidas.append(f"Puesto de trabajo: {requerimiento.equipo} / {requerimiento.sistema_operativo}")
        if asignacion_puesto and asignacion_puesto.estado == "COMPLETADA":
            solicitudes_respondidas.append(f"Puesto asignado: {asignacion_puesto.puesto_fisico.codigo_puesto}")

    if request.GET.get("volver") == "servicios" and es_servicios(request.user):
        volver_url = "panel_servicios"
        volver_texto = "Volver a Servicios"
    else:
        volver_url = "rrhh_ingresos_listar"
        volver_texto = "Volver a procesos"

    return render(request, "accounts/acta_final.html", {
        "ingreso": ingreso,
        "fecha_creacion_acta": timezone.localtime(),
        "solicitudes_pedidas": solicitudes_pedidas,
        "solicitudes_respondidas": solicitudes_respondidas,
        "cursos": cursos,
        "aplicativos": aplicativos,
        "dotaciones": dotaciones,
        "requerimiento": requerimiento,
        "asignacion_puesto": asignacion_puesto,
        "volver_url": volver_url,
        "volver_texto": volver_texto,
    })

@login_required
def rrhh_ingreso_cancelar(request, ingreso_id):
    ingreso = get_object_or_404(Ingreso, id=ingreso_id)
    error = None

    if request.method == "POST":
        observacion = request.POST.get("observacion_cancelacion", "").strip()
        if not observacion:
            error = "Escribe una observación para cancelar el proceso."
            return render(request, "accounts/ingreso_cancelar.html", {"ingreso": ingreso, "error": error})

        ingreso.estado = "CANCELADO"
        ingreso.observacion_cancelacion = observacion
        ingreso.fecha_cancelacion = timezone.now()
        ingreso.save(update_fields=["estado", "observacion_cancelacion", "fecha_cancelacion"])
        return redirect("rrhh_acta_final", ingreso_id=ingreso.id)

    return render(request, "accounts/ingreso_cancelar.html", {"ingreso": ingreso, "error": error})
