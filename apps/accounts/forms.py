from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'display_name', 'email', 'role', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.display_name = self.cleaned_data['display_name']
        user.role = self.cleaned_data['role']
        if commit:
            user.save()
        return user


class AccountSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('display_name', 'first_name', 'last_name', 'username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['display_name'].required = True
        self.fields['display_name'].help_text = 'Public name shown across your account experience.'
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['username'].help_text = 'Used for login and account identity.'
        self.fields['email'].required = True
