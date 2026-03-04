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
from accounts.views import panel_rrhh, redireccion_por_rol
from accounts.views import panel_jefe_credito, jefe_credito_seleccionar

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('rrhh/', redireccion_por_rol, name='redireccion_por_rol'),
    path('panel-rrhh/', panel_rrhh, name='panel_rrhh'),
    path("jefe-credito/", panel_jefe_credito, name="panel_jefe_credito"),
    path("jefe-credito/ingreso/<int:ingreso_id>/", jefe_credito_seleccionar, name="jefe_credito_seleccionar"),
]