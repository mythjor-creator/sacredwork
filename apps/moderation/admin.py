from django.contrib import admin

from .models import ModerationDecision


@admin.register(ModerationDecision)
class ModerationDecisionAdmin(admin.ModelAdmin):
	list_display = ('decision', 'profile', 'service', 'decided_by', 'created_at')
	list_filter = ('decision',)
	search_fields = ('profile__business_name', 'service__name', 'decided_by__username')
