from django import forms
from .models import Pari

class PariForm(forms.ModelForm):
    class Meta:
        model = Pari
        fields = ["description"]
        widgets = {
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Décris le pari..."
            })
        }
