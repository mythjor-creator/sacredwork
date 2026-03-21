from django.contrib import admin
from django.contrib import messages as django_messages
from django.db.models import Count, Max
from django.utils.html import format_html
from django.utils import timezone

from .models import PractitionerWaitlistProfile, StatusTransition
from .emails import send_status_change_notification


@admin.action(description='Mark selected as Invited')
def mark_as_invited(modeladmin, request, queryset):
    now = timezone.now()
    
    # Capture old statuses before update
    profiles_data = {}
    for profile in queryset:
        profiles_data[profile.id] = profile.status
    
    # Update status for all profiles
    updated = queryset.update(
        status=PractitionerWaitlistProfile.Status.INVITED,
        status_changed_at=now,
    )
    
    # Create transition records and send notifications
    for profile_id, old_status in profiles_data.items():
        transition = StatusTransition.objects.create(
            profile_id=profile_id,
            from_status=old_status,
            to_status=PractitionerWaitlistProfile.Status.INVITED,
            changed_at=now,
            changed_by=request.user,
        )
        # Send status change email
        send_status_change_notification(transition)
    
    modeladmin.message_user(request, f'{updated} profile(s) marked as Invited and notified via email.', django_messages.SUCCESS)


@admin.action(description='Mark selected as Test data')
def mark_as_test_data(modeladmin, request, queryset):
    updated = queryset.update(is_test_data=True)
    modeladmin.message_user(request, f'{updated} profile(s) marked as test data.', django_messages.SUCCESS)


@admin.action(description='Mark selected as Real data')
def mark_as_real_data(modeladmin, request, queryset):
    updated = queryset.update(is_test_data=False)
    modeladmin.message_user(request, f'{updated} profile(s) marked as real data.', django_messages.SUCCESS)


@admin.register(PractitionerWaitlistProfile)
class PractitionerWaitlistProfileAdmin(admin.ModelAdmin):
    change_list_template = 'admin/waitlist/practitionerwaitlistprofile/change_list.html'
    list_display = (
        'full_name',
        'email',
        'is_test_data',
        'signup_tier',
        'practice_type',
        'is_founding_member',
        'status',
        'location',
        'offers_in_person',
        'status_changed_at',
        'created_at',
    )
    list_filter = ('is_test_data', 'signup_tier', 'is_founding_member', 'practice_type', 'status', 'is_virtual', 'offers_in_person')
    search_fields = ('business_name', 'full_name', 'email', 'headline', 'modalities', 'location')
    readonly_fields = ('status_changed_at', 'created_at', 'transition_history')
    actions = [mark_as_invited, mark_as_test_data, mark_as_real_data]

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        if not hasattr(response, 'context_data'):
            return response

        changelist = response.context_data.get('cl')
        if changelist is None:
            return response

        all_profiles = self.model.objects.all()
        filtered_profiles = changelist.queryset

        response.context_data['waitlist_summary'] = {
            'total_count': all_profiles.count(),
            'filtered_count': filtered_profiles.count(),
            'real_count': all_profiles.filter(is_test_data=False).count(),
            'test_count': all_profiles.filter(is_test_data=True).count(),
            'founding_count': all_profiles.filter(is_founding_member=True).count(),
            'filtered_founding_count': filtered_profiles.filter(is_founding_member=True).count(),
            'latest_signup_at': all_profiles.aggregate(latest=Max('created_at'))['latest'],
            'status_cards': self._build_status_cards(all_profiles, filtered_profiles),
        }
        return response

    def _build_status_cards(self, all_profiles, filtered_profiles):
        totals_by_status = {
            row['status']: row['count']
            for row in all_profiles.values('status').annotate(count=Count('id'))
        }
        filtered_by_status = {
            row['status']: row['count']
            for row in filtered_profiles.values('status').annotate(count=Count('id'))
        }
        return [
            {
                'label': label,
                'value': totals_by_status.get(value, 0),
                'filtered_value': filtered_by_status.get(value, 0),
            }
            for value, label in PractitionerWaitlistProfile.Status.choices
        ]
    
    def transition_history(self, obj: PractitionerWaitlistProfile) -> str:
        """Display transition history for a profile."""
        if not obj.pk:
            return 'No transitions yet'
        
        transitions = obj.status_transitions.all()[:20]  # Last 20
        if not transitions:
            return 'No status transitions recorded'
        
        lines = ['<table style="border-collapse: collapse; width: 100%;"><tr><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">From</th><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">To</th><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">When</th><th style="border: 1px solid #ddd; padding: 8px; text-align: left;">By</th></tr>']
        for t in transitions:
            by_user = t.changed_by.username if t.changed_by else 'system'
            lines.append(f'<tr><td style="border: 1px solid #ddd; padding: 8px;">{t.get_from_status_display()}</td><td style="border: 1px solid #ddd; padding: 8px;">{t.get_to_status_display()}</td><td style="border: 1px solid #ddd; padding: 8px;">{t.changed_at.strftime("%Y-%m-%d %H:%M")}</td><td style="border: 1px solid #ddd; padding: 8px;">{by_user}</td></tr>')
        lines.append('</table>')
        return format_html('{}'.format(''.join(lines)))
    
    transition_history.short_description = 'Status Transition History'


@admin.register(StatusTransition)
class StatusTransitionAdmin(admin.ModelAdmin):
    list_display = ('profile', 'from_status', 'to_status', 'changed_at', 'changed_by')
    list_filter = ('to_status', 'changed_at', 'changed_by')
    search_fields = ('profile__full_name', 'profile__email')
    readonly_fields = ('profile', 'from_status', 'to_status', 'changed_at', 'created_at')
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
