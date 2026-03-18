from django import forms
from django.forms import inlineformset_factory

from .models import Service, ServiceTier


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
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
        }


ServiceTierFormSet = inlineformset_factory(
    Service,
    ServiceTier,
    fields=('name', 'description', 'duration_minutes', 'price_cents', 'sort_order', 'is_active'),
    extra=1,
    can_delete=True,
)
