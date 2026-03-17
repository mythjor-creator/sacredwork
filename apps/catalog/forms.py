from django import forms

from .models import Service


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = (
            'category',
            'name',
            'description',
            'duration_minutes',
            'price_cents',
            'delivery_format',
            'is_active',
        )
