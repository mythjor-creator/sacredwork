from django import forms


class ReportProblemForm(forms.Form):
    email = forms.EmailField(required=False)
    summary = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'placeholder': 'Short summary'}),
    )
    details = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'What happened, and what did you expect?'}),
    )
