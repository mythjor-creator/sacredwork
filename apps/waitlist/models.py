from django.db import models


class PractitionerWaitlistProfile(models.Model):
    class PracticeType(models.TextChoices):
        WELLNESS = 'wellness', 'Wellness'
        SPIRITUAL = 'spiritual', 'Spiritual'
        BEAUTY = 'beauty', 'Beauty'
        COACHING = 'coaching', 'Coaching'
        OTHER = 'other', 'Other'

    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=180, blank=True, default='')
    headline = models.CharField(max_length=220)
    modalities = models.CharField(max_length=255, help_text='Comma-separated offerings')
    practice_type = models.CharField(max_length=20, choices=PracticeType.choices)
    location = models.CharField(max_length=120, blank=True)
    is_virtual = models.BooleanField(default=True)
    offers_in_person = models.BooleanField(default=False)
    years_experience = models.PositiveSmallIntegerField(default=0)
    website_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.full_name} ({self.email})'
