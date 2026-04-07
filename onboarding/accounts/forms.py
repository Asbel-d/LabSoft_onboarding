from django import forms
from .models import CatalogoItem
from .models import Ingreso

class SeleccionCursosAppsForm(forms.Form):
    cursos = forms.ModelMultipleChoiceField(
        queryset=CatalogoItem.objects.filter(tipo="CURSO").order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Cursos"
    )

    aplicativos = forms.ModelMultipleChoiceField(
        queryset=CatalogoItem.objects.filter(tipo="APLICACION").order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Aplicativos"
    )


class SeleccionAplicativosForm(forms.Form):
    aplicativos = forms.ModelMultipleChoiceField(
        queryset=CatalogoItem.objects.filter(tipo="APLICACION").order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Aplicativos"
    )

class IngresoForm(forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = [
            "codigo_proceso", "nombre_empleado", "tipo_documento", "documento",
            "fecha_ingreso", "puesto_organizacional"
        ]
        widgets = {
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
        }