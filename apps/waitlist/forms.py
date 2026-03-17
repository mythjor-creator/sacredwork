from django import forms

from .models import PractitionerWaitlistProfile


class PractitionerWaitlistForm(forms.ModelForm):
    class Meta:
        model = PractitionerWaitlistProfile
        fields = (
            'full_name',
            'email',
            'business_name',
            'headline',
            'modalities',
            'practice_type',
            'location',
            'is_virtual',
            'years_experience',
            'website_url',
            'notes',
        )

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if PractitionerWaitlistProfile.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already on the waitlist.')
        return email
