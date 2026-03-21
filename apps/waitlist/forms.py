from django import forms

from config.test_data import email_is_test_data

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
            'offers_in_person',
            'years_experience',
            'website_url',
            'notes',
            'is_founding_member',
        )
        widgets = {
            'is_founding_member': forms.HiddenInput(),
        }
        labels = {
            'full_name': 'Practitioner name',
            'email': 'Email',
            'business_name': 'Business name (optional)',
            'headline': 'Headline',
            'modalities': 'Modalities',
            'practice_type': 'Primary practice type',
            'location': 'Location',
            'is_virtual': 'Offer virtual sessions',
            'offers_in_person': 'Offer in-person sessions',
            'years_experience': 'Years of experience',
            'website_url': 'Website URL',
            'notes': 'Anything else we should know?',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['business_name'].required = False

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if PractitionerWaitlistProfile.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already on the waitlist.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        is_virtual = cleaned_data.get('is_virtual')
        offers_in_person = cleaned_data.get('offers_in_person')
        if not is_virtual and not offers_in_person:
            raise forms.ValidationError('Select at least one session format: virtual or in-person.')
        return cleaned_data

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.is_test_data = email_is_test_data(profile.email)
        if commit:
            profile.save()
        return profile
