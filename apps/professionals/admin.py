from django.contrib import admin
from django.db import transaction
from django.contrib import messages as django_messages

from apps.moderation.models import ModerationDecision

from .models import ProfessionalProfile


@admin.action(description='Mark selected as Verified')
def mark_as_verified(modeladmin, request, queryset):
	updated = queryset.update(is_verified=True)
	modeladmin.message_user(request, f'{updated} profile(s) marked as verified.', django_messages.SUCCESS)


@admin.action(description='Remove Verified badge')
def mark_as_unverified(modeladmin, request, queryset):
	updated = queryset.update(is_verified=False)
	modeladmin.message_user(request, f'Verified badge removed from {updated} profile(s).', django_messages.SUCCESS)


@admin.register(ProfessionalProfile)
class ProfessionalProfileAdmin(admin.ModelAdmin):
	list_display = ('display_name', 'user', 'approval_status', 'is_verified', 'completeness_percent', 'is_visible', 'is_virtual')
	list_filter = ('approval_status', 'is_verified', 'is_visible', 'is_virtual')
	search_fields = ('business_name', 'user__username', 'headline', 'modalities')
	actions = ['approve_profiles', 'reject_profiles', mark_as_verified, mark_as_unverified]

	@admin.display(description='Complete %')
	def completeness_percent(self, obj):
		return f'{obj.completeness_percent}%'

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
