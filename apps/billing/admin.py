from django.contrib import admin

from .models import ProfessionalSubscription, SubscriptionInvoice, SubscriptionPlan


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'amount_cents', 'billing_interval', 'founding_only', 'is_active')
    list_filter = ('billing_interval', 'founding_only', 'is_active')
    search_fields = ('name', 'code', 'stripe_price_id')
    ordering = ('display_order', 'amount_cents', 'name')


@admin.register(ProfessionalSubscription)
class ProfessionalSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        'professional',
        'plan',
        'status',
        'founding_member_rate_locked',
        'cancel_at_period_end',
        'current_period_end',
    )
    list_filter = ('status', 'founding_member_rate_locked', 'cancel_at_period_end')
    search_fields = (
        'professional__user__username',
        'professional__user__email',
        'professional__business_name',
        'stripe_customer_id',
        'stripe_subscription_id',
    )
    autocomplete_fields = ('professional', 'plan')


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ('stripe_invoice_id', 'subscription', 'status', 'amount_due_cents', 'amount_paid_cents', 'paid_at')
    list_filter = ('status', 'currency')
    search_fields = ('stripe_invoice_id', 'subscription__professional__user__email')
    autocomplete_fields = ('subscription',)
