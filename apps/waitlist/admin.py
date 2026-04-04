from django.contrib import admin
from django.db.models import Count
from .models import InviteCode, PractitionerWaitlistProfile, StatusTransition, WaitlistLead


def mark_as_invited(modeladmin, request, queryset):
    """Admin action: move selected profiles to INVITED status and record who made the change."""
    count = 0
    for profile in queryset.exclude(status=PractitionerWaitlistProfile.Status.INVITED):
        profile.status = PractitionerWaitlistProfile.Status.INVITED
        profile.save()
        transition = (
            StatusTransition.objects
            .filter(profile=profile, to_status=PractitionerWaitlistProfile.Status.INVITED)
            .order_by('-changed_at')
            .first()
        )
        if transition and transition.changed_by is None:
            transition.changed_by = request.user
            transition.save(update_fields=['changed_by'])
        count += 1
    modeladmin.message_user(request, f'{count} profile(s) marked as Invited.')


mark_as_invited.short_description = 'Mark selected as Invited'

@admin.register(WaitlistLead)
class WaitlistLeadAdmin(admin.ModelAdmin):
    list_display = (
        'invited_yn',
        'confirmation_email_sent',
        'name_last_first',
        'referred_by_name',
        'current_referral_code',
        'current_referral_uses',
        'email',
        'notes',
    )
    search_fields = ('name', 'email', 'notes')
    list_filter = ('created_at', 'confirmation_email_sent')
    readonly_fields = ('created_at', 'confirmation_email_error')

    @admin.display(boolean=True, description='Invited (y/n)')
    def invited_yn(self, obj):
        return bool(obj.invite_code_id)

    @admin.display(description='Name')
    def name_last_first(self, obj):
        parts = obj.name.strip().split()
        if len(parts) < 2:
            return obj.name
        return f"{parts[-1]}, {' '.join(parts[:-1])}"

    @admin.display(description='Referred By')
    def referred_by_name(self, obj):
        if obj.invite_code and obj.invite_code.owner:
            return obj.invite_code.owner.name
        return '-'

    @admin.display(description='Referral Code')
    def current_referral_code(self, obj):
        code = obj.owned_invite_codes.order_by('-created_at').first()
        return code.code if code else '-'

    @admin.display(description='#uses')
    def current_referral_uses(self, obj):
        code = obj.owned_invite_codes.order_by('-created_at').first()
        if not code:
            return '-'
        return WaitlistLead.objects.filter(invite_code=code).count()

    fieldsets = (
        (None, {
            'fields': (
                'name',
                'email',
                'role',
                'invite_code',
                'notes',
                'confirmation_email_sent',
                'confirmation_email_error',
                'created_at',
            )
        }),
    )

@admin.register(PractitionerWaitlistProfile)
class PractitionerWaitlistProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'status', 'signup_tier', 'is_founding_member', 'practice_type', 'created_at')
    list_filter = ('status', 'signup_tier', 'is_founding_member', 'practice_type', 'created_at')
    search_fields = ('full_name', 'email', 'business_name')
    readonly_fields = ('created_at', 'status_changed_at')
    actions = [mark_as_invited]

    def _build_tier_cards(self, base_qs, filtered_qs):
        tier_counts = {
            item['signup_tier']: item['count']
            for item in base_qs.values('signup_tier').annotate(count=Count('id'))
        }
        filtered_counts = {
            item['signup_tier']: item['count']
            for item in filtered_qs.values('signup_tier').annotate(count=Count('id'))
        }
        return [
            {
                'label': label,
                'value': tier_counts.get(value, 0),
                'filtered_value': filtered_counts.get(value, 0),
            }
            for value, label in PractitionerWaitlistProfile.SignupTier.choices
        ]


@admin.register(InviteCode)
class InviteCodeAdmin(admin.ModelAdmin):
    list_display = (
        'code',
        'admin_owner',
        'owner',
        'is_active',
        'uses_remaining',
        'created_at',
    )
    search_fields = (
        'code',
        'owner__name',
        'owner__email',
        'admin_owner__username',
        'admin_owner__email',
    )
    list_filter = ('is_active', 'admin_owner', 'created_at')
    readonly_fields = ('created_at',)
