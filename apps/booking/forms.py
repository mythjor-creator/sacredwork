from datetime import datetime

from django import forms
from django.utils import timezone

from .models import AvailabilityWindow


class AvailabilityWindowForm(forms.ModelForm):
    class Meta:
        model = AvailabilityWindow
        fields = ('weekday', 'start_time', 'end_time', 'is_active')

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time and start_time >= end_time:
            self.add_error('end_time', 'End time must be after start time.')
        return cleaned_data


class BookingRequestForm(forms.Form):
    slot = forms.ChoiceField(choices=())
    intake_notes = forms.CharField(widget=forms.Textarea, required=False)

    def __init__(self, *args, slots=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.slots = slots or []
        self.fields['slot'].choices = [
            (slot['start_at'].isoformat(), slot['label']) for slot in self.slots
        ]
        if not self.slots:
            self.fields['slot'].help_text = 'No upcoming slots are available yet.'

    def clean(self):
        cleaned_data = super().clean()
        raw_value = cleaned_data.get('slot')
        valid_values = {slot['start_at'].isoformat() for slot in self.slots}
        if raw_value:
            if raw_value not in valid_values:
                self.add_error('slot', 'Please select an available slot.')
            else:
                start_at = datetime.fromisoformat(raw_value)
                if timezone.is_naive(start_at):
                    start_at = timezone.make_aware(start_at)
                cleaned_data['start_at'] = start_at
        return cleaned_data
