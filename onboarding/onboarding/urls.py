"""
URL configuration for onboarding project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from accounts.views import (
    panel_rrhh, redireccion_por_rol, panel_jefe, jefe_seleccionar,
    rrhh_ingreso_crear, rrhh_ingreso_editar, rrhh_ingreso_cancelar, rrhh_ingresos_listar,
    rrhh_asignar_cursos, panel_tecnologia, tecnologia_asignar_aplicativos,
    panel_talento_humano, talento_confirmar_cursos,
    panel_servicios, servicios_finalizar_ingreso,
    rrhh_acta_final,
    puesto_info
)

urlpatterns = [
    path('', redireccion_por_rol, name='home'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('rrhh/', redireccion_por_rol, name='redireccion_por_rol'),
    path('panel-rrhh/', panel_rrhh, name='panel_rrhh'),
    path('panel-tecnologia/', panel_tecnologia, name='panel_tecnologia'),
    path('panel-talento-humano/', panel_talento_humano, name='panel_talento_humano'),
    path('panel-servicios/', panel_servicios, name='panel_servicios'),
    path("jefe/", panel_jefe, name="panel_jefe"),
    path("jefe/ingreso/<int:ingreso_id>/", jefe_seleccionar, name="jefe_seleccionar"),
    path("api/puestos/<int:puesto_id>/info/", puesto_info, name="puesto_info"),
    path("rrhh/ingresos/", rrhh_ingresos_listar, name="rrhh_ingresos_listar"),
    path("rrhh/ingresos/<int:ingreso_id>/asignar-cursos/", rrhh_asignar_cursos, name="rrhh_asignar_cursos"),
    path("rrhh/ingresos/crear/", rrhh_ingreso_crear, name="rrhh_ingreso_crear"),
    path("rrhh/ingresos/<int:ingreso_id>/editar/", rrhh_ingreso_editar, name="rrhh_ingreso_editar"),
    path("rrhh/ingresos/<int:ingreso_id>/cancelar/", rrhh_ingreso_cancelar, name="rrhh_ingreso_cancelar"),
    path("tecnologia/ingresos/<int:ingreso_id>/asignar-aplicativos/", tecnologia_asignar_aplicativos, name="tecnologia_asignar_aplicativos"),
    path("talento/ingresos/<int:ingreso_id>/confirmar-cursos/", talento_confirmar_cursos, name="talento_confirmar_cursos"),
    path("servicios/ingresos/<int:ingreso_id>/finalizar/", servicios_finalizar_ingreso, name="servicios_finalizar_ingreso"),
    path("rrhh/ingresos/<int:ingreso_id>/acta-final/", rrhh_acta_final, name="rrhh_acta_final"),
]
