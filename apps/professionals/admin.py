from django.contrib import admin
from django.db import transaction

from apps.moderation.models import ModerationDecision

from .models import ProfessionalProfile


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(admin.ModelAdmin):
	list_display = ('business_name', 'user', 'approval_status', 'is_visible', 'is_virtual')
	list_filter = ('approval_status', 'is_visible', 'is_virtual')
	search_fields = ('business_name', 'user__username', 'headline', 'modalities')
	actions = ['approve_profiles', 'reject_profiles']

	@admin.action(description='Approve selected profiles and make visible')
	def approve_profiles(self, request, queryset):
		count = 0
		with transaction.atomic():
			for profile in queryset.select_for_update():
				profile.approval_status = ProfessionalProfile.ApprovalStatus.APPROVED
				profile.is_visible = True
				profile.save(update_fields=['approval_status', 'is_visible', 'updated_at'])
				ModerationDecision.objects.create(
					profile=profile,
					decided_by=request.user,
					decision=ModerationDecision.Decision.APPROVED,
				)
				count += 1
		self.message_user(request, f'{count} profile(s) approved and published.')

	@admin.action(description='Reject selected profiles')
	def reject_profiles(self, request, queryset):
		count = 0
		with transaction.atomic():
			for profile in queryset.select_for_update():
				profile.approval_status = ProfessionalProfile.ApprovalStatus.REJECTED
				profile.is_visible = False
				profile.save(update_fields=['approval_status', 'is_visible', 'updated_at'])
				ModerationDecision.objects.create(
					profile=profile,
					decided_by=request.user,
					decision=ModerationDecision.Decision.REJECTED,
				)
				count += 1
		self.message_user(request, f'{count} profile(s) rejected.')
