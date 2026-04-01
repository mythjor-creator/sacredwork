from django.contrib import admin
from .models import WaitlistLead, InviteCode

@admin.register(WaitlistLead)
class WaitlistLeadAdmin(admin.ModelAdmin):
    list_display = (
        'invited_yn',
        'name_last_first',
        'referred_by_name',
        'current_referral_code',
        'current_referral_uses',
        'email',
        'notes',
    )
    search_fields = ('name', 'email', 'notes')
    list_filter = ('created_at',)
    readonly_fields = ('created_at',)

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
