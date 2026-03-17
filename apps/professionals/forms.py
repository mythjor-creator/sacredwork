from django import forms

from .models import ProfessionalProfile


class ProfessionalOnboardingForm(forms.ModelForm):
    class Meta:
        model = ProfessionalProfile
        fields = (
            'business_name',
            'headline',
            'bio',
            'modalities',
            'location',
            'is_virtual',
            'years_experience',
            'profile_image_url',
        )
        labels = {
            'business_name': 'Business name (optional)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['business_name'].required = False
