from django.contrib import admin
from django.contrib import messages as django_messages
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


@admin.register(PractitionerWaitlistProfile)
class PractitionerWaitlistProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name',
        'email',
        'practice_type',
        'status',
        'location',
        'offers_in_person',
        'status_changed_at',
        'created_at',
    )
    list_filter = ('practice_type', 'status', 'is_virtual', 'offers_in_person')
    search_fields = ('business_name', 'full_name', 'email', 'headline', 'modalities', 'location')
    readonly_fields = ('status_changed_at', 'created_at', 'transition_history')
    actions = [mark_as_invited]
    
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
        return '\n'.join(lines)
    
    transition_history.short_description = 'Status Transition History'
    transition_history.allow_tags = True


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
