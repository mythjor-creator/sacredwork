from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].help_text = 'Describe what the client can expect from this service.'


class ServiceTierForm(forms.ModelForm):
    class Meta:
        model = ServiceTier
        fields = ('name', 'description', 'duration_minutes', 'price_cents', 'sort_order', 'is_active')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'name': forms.TextInput(attrs={'placeholder': 'Intro, Standard, Deep Dive'}),
            'duration_minutes': forms.NumberInput(attrs={'placeholder': 'Optional override'}),
            'price_cents': forms.NumberInput(attrs={'placeholder': 'e.g. 15000 for $150.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['description'].required = False
        self.fields['duration_minutes'].required = False
        self.fields['name'].help_text = 'Short label clients will see on your profile.'
        self.fields['price_cents'].help_text = 'Enter price in cents to match the rest of the system.'


class BaseServiceTierInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen_names = set()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue

            name = (form.cleaned_data.get('name') or '').strip()
            price_cents = form.cleaned_data.get('price_cents')
            duration_minutes = form.cleaned_data.get('duration_minutes')

            if not name and not price_cents and not duration_minutes:
                continue

            normalized_name = name.lower()
            if normalized_name in seen_names:
                form.add_error('name', 'Tier names must be unique within a service.')
            elif normalized_name:
                seen_names.add(normalized_name)


ServiceTierFormSet = inlineformset_factory(
    Service,
    ServiceTier,
    form=ServiceTierForm,
    fields=('name', 'description', 'duration_minutes', 'price_cents', 'sort_order', 'is_active'),
    extra=1,
    can_delete=True,
    formset=BaseServiceTierInlineFormSet,
)
