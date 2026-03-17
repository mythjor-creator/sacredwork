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
