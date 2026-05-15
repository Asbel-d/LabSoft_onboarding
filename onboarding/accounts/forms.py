from django import forms
from django.utils import timezone
from .models import CatalogoItem
from .models import Ingreso


TIPOS_DOCUMENTO = [
    ("C.C", "C.C"),
    ("C.E", "C.E"),
    ("PASAPORTE", "PASAPORTE"),
]


def generar_codigo_proceso():
    fecha = timezone.localdate().strftime("%Y%m%d")
    ultimo_ingreso = Ingreso.objects.order_by("-id").first()
    consecutivo = (ultimo_ingreso.id + 1) if ultimo_ingreso else 1

    while True:
        codigo = f"ING-{fecha}-{consecutivo:04d}"
        if not Ingreso.objects.filter(codigo_proceso=codigo).exists():
            return codigo
        consecutivo += 1

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


class ImportarHistoricoForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo historico",
        help_text="Sube un archivo .csv o .xlsx exportado desde la base anterior.",
    )
    actualizar_existentes = forms.BooleanField(
        required=False,
        initial=True,
        label="Actualizar procesos existentes por codigo",
    )


class IngresoForm(forms.ModelForm):
    def __init__(self, *args, allow_past_date=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.allow_past_date = allow_past_date
        self.fields["tipo_documento"].choices = TIPOS_DOCUMENTO
        self.fields["codigo_proceso"].widget.attrs["readonly"] = "readonly"
        self.fields["codigo_proceso"].required = False

        if not self.instance.pk and not self.initial.get("codigo_proceso"):
            self.initial["codigo_proceso"] = generar_codigo_proceso()

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
            "tipo_documento": forms.Select(choices=TIPOS_DOCUMENTO),
        }

    def clean_codigo_proceso(self):
        codigo_proceso = self.cleaned_data.get("codigo_proceso")
        return codigo_proceso or generar_codigo_proceso()

    def clean_fecha_ingreso(self):
        fecha_ingreso = self.cleaned_data.get("fecha_ingreso")
        if fecha_ingreso and not self.allow_past_date and fecha_ingreso < timezone.localdate():
            raise forms.ValidationError("La fecha del proceso debe ser hoy o una fecha posterior.")
        return fecha_ingreso
