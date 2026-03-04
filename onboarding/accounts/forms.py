from django import forms
from .models import CatalogoItem

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