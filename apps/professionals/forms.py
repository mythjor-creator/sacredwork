from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import ProfessionalCredential, ProfessionalProfile, ProfileGalleryImage


class ProfessionalOnboardingForm(forms.ModelForm):
    class Meta:
        model = ProfessionalProfile
        fields = (
            'business_name',
            'headline',
            'bio',
            'long_bio',
            'modalities',
            'location',
            'is_virtual',
            'years_experience',
            'profile_image_url',
            'profile_photo',
        )
        labels = {
            'business_name': 'Business name (optional)',
        }
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4}),
            'long_bio': forms.Textarea(attrs={'rows': 7}),
            'modalities': forms.TextInput(attrs={'placeholder': 'e.g. reiki, somatic coaching, breathwork'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['business_name'].required = False
        self.fields['long_bio'].required = False
        self.fields['profile_image_url'].required = False
        self.fields['profile_photo'].required = False
        self.fields['bio'].help_text = 'Short profile summary shown in search results.'
        self.fields['long_bio'].help_text = 'Optional deeper narrative for your full profile page.'
        self.fields['profile_photo'].help_text = 'Recommended: square photo, at least 600x600.'
        self.fields['profile_image_url'].help_text = 'Optional fallback URL if you host your photo elsewhere.'


class ProfileGalleryImageForm(forms.ModelForm):
    """Custom form for gallery images that allows empty submissions."""
    class Meta:
        model = ProfileGalleryImage
        fields = ('image', 'caption', 'sort_order', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make image optional to allow empty gallery entries
        self.fields['image'].required = False
        self.fields['caption'].required = False


class BaseCredentialInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        for form in self.forms:
            if not hasattr(form, 'cleaned_data'):
                continue
            if form.cleaned_data.get('DELETE'):
                continue
            issued_on = form.cleaned_data.get('issued_on')
            expires_on = form.cleaned_data.get('expires_on')
            if issued_on and expires_on and expires_on < issued_on:
                form.add_error('expires_on', 'Expiration date must be after issued date.')


GalleryImageFormSet = inlineformset_factory(
    ProfessionalProfile,
    ProfileGalleryImage,
    form=ProfileGalleryImageForm,
    fields=('image', 'caption', 'sort_order', 'is_active'),
    extra=1,
    can_delete=True,
)


CredentialFormSet = inlineformset_factory(
    ProfessionalProfile,
    ProfessionalCredential,
    fields=(
        'credential_type',
        'title',
        'organization',
        'license_number',
        'issued_on',
        'expires_on',
        'verification_url',
        'notes',
        'sort_order',
        'is_active',
    ),
    extra=1,
    can_delete=True,
    formset=BaseCredentialInlineFormSet,
)
