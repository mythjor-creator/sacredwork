from django.contrib import admin
from django.db import transaction
from django.contrib import messages as django_messages

from apps.billing.models import ProfessionalSubscription, SubscriptionPlan
from apps.moderation.models import ModerationDecision
from apps.waitlist.models import PractitionerWaitlistProfile

from .models import ProfessionalCredential, ProfessionalProfile, ProfileGalleryImage


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
	list_display = (
		'display_name',
		'user',
		'approval_status',
		'subscription_status',
		'is_verified',
		'completeness_percent',
		'is_visible',
		'is_virtual',
	)
	list_filter = ('approval_status', 'subscription_status', 'is_verified', 'is_visible', 'is_virtual')
	search_fields = ('business_name', 'user__username', 'headline', 'modalities')
	actions = ['approve_profiles', 'reject_profiles', mark_as_verified, mark_as_unverified]

	@admin.display(description='Complete %')
	def completeness_percent(self, obj):
		return f'{obj.completeness_percent}%'

	@admin.action(description='Approve selected profiles and make visible')
	def approve_profiles(self, request, queryset):
		count = 0
		founding_count = 0
		default_plan = SubscriptionPlan.objects.filter(code='founding-annual', is_active=True).first()
		with transaction.atomic():
			for profile in queryset.select_for_update():
				waitlist_profile = PractitionerWaitlistProfile.objects.filter(
					email__iexact=profile.user.email,
				).first()
				if profile.subscription_status == ProfessionalProfile.SubscriptionStatus.NOT_STARTED:
					profile.subscription_status = ProfessionalProfile.SubscriptionStatus.PRELAUNCH
				profile.approval_status = ProfessionalProfile.ApprovalStatus.APPROVED
				profile.is_visible = True
				profile.save(update_fields=['approval_status', 'subscription_status', 'is_visible', 'updated_at'])
				if waitlist_profile is not None and waitlist_profile.is_founding_member:
					_, created = ProfessionalSubscription.objects.get_or_create(
						professional=profile,
						defaults={
							'plan': default_plan,
							'status': ProfessionalSubscription.Status.PENDING_LAUNCH,
							'founding_member_rate_locked': True,
						},
					)
					if created:
						founding_count += 1
				ModerationDecision.objects.create(
					profile=profile,
					decided_by=request.user,
					decision=ModerationDecision.Decision.APPROVED,
				)
				count += 1
		message = f'{count} profile(s) approved and published.'
		if founding_count:
			message += f' {founding_count} founding subscription record(s) prepared for launch billing.'
		self.message_user(request, message)

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


@admin.register(ProfileGalleryImage)
class ProfileGalleryImageAdmin(admin.ModelAdmin):
	list_display = ('profile', 'caption', 'sort_order', 'is_active', 'created_at')
	list_filter = ('is_active',)
	search_fields = ('profile__user__username', 'profile__business_name', 'caption')


@admin.register(ProfessionalCredential)
class ProfessionalCredentialAdmin(admin.ModelAdmin):
	list_display = ('profile', 'credential_type', 'title', 'organization', 'is_active')
	list_filter = ('credential_type', 'is_active')
	search_fields = ('profile__user__username', 'profile__business_name', 'title', 'organization')
