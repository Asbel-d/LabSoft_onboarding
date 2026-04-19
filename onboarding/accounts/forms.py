from django import forms
from django.utils import timezone
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

    dotaciones = forms.ModelMultipleChoiceField(
        queryset=CatalogoItem.objects.filter(tipo="DOTACION").order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Dotación y uniformes"
    )

    requiere_puesto_trabajo = forms.BooleanField(
        required=False,
        label="Solicitar puesto de trabajo físico"
    )
    equipo = forms.CharField(
        required=False,
        max_length=200,
        label="Equipo requerido",
        widget=forms.TextInput(attrs={"placeholder": "Ej: portátil, escritorio, monitor"})
    )
    sistema_operativo = forms.CharField(
        required=False,
        max_length=200,
        label="Sistema operativo",
        widget=forms.TextInput(attrs={"placeholder": "Ej: Windows 11"})
    )

    def clean(self):
        cleaned_data = super().clean()
        requiere_puesto = cleaned_data.get("requiere_puesto_trabajo")

        if requiere_puesto:
            if not cleaned_data.get("equipo"):
                self.add_error("equipo", "Indica el equipo requerido para el puesto de trabajo.")
            if not cleaned_data.get("sistema_operativo"):
                self.add_error("sistema_operativo", "Indica el sistema operativo requerido.")

        return cleaned_data


class SeleccionAplicativosForm(forms.Form):
    aplicativos = forms.ModelMultipleChoiceField(
        queryset=CatalogoItem.objects.filter(tipo="APLICACION").order_by("nombre"),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Aplicativos"
    )

class IngresoForm(forms.ModelForm):
    def __init__(self, *args, allow_past_date=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_past_date = allow_past_date
        if not allow_past_date:
            self.fields["fecha_ingreso"].widget.attrs["min"] = timezone.localdate().isoformat()

    class Meta:
        model = Ingreso
        fields = [
            "codigo_proceso", "nombre_empleado", "tipo_documento", "documento",
            "fecha_ingreso", "puesto_organizacional"
        ]
        widgets = {
            "fecha_ingreso": forms.DateInput(attrs={"type": "date"}),
        }

    def clean_fecha_ingreso(self):
        fecha_ingreso = self.cleaned_data.get("fecha_ingreso")
        if fecha_ingreso and not self.allow_past_date and fecha_ingreso < timezone.localdate():
            raise forms.ValidationError("La fecha del proceso debe ser hoy o una fecha posterior.")
        return fecha_ingreso
