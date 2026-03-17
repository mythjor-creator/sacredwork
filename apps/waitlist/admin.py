from django.contrib import admin

from .models import PractitionerWaitlistProfile


@admin.register(PractitionerWaitlistProfile)
class PractitionerWaitlistProfileAdmin(admin.ModelAdmin):
    list_display = (
        'business_name',
        'full_name',
        'email',
        'practice_type',
        'is_virtual',
        'offers_in_person',
        'created_at',
    )
    list_filter = ('practice_type', 'is_virtual', 'offers_in_person')
    search_fields = ('business_name', 'full_name', 'email', 'headline', 'modalities')
