import logging

from django.contrib import admin
from django.contrib import messages as django_messages

from .models import BillingWebhookEvent, ProfessionalSubscription, SubscriptionInvoice, SubscriptionPlan
from .payments import sync_subscription_from_stripe


logger = logging.getLogger(__name__)


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
    actions = ('sync_now',)

    @admin.action(description='Sync selected from Stripe now')
    def sync_now(self, request, queryset):
        synced = 0
        skipped = 0
        failed = 0

        for subscription in queryset.select_related('professional'):
            if not (subscription.stripe_subscription_id or '').strip():
                skipped += 1
                continue
            try:
                if sync_subscription_from_stripe(subscription):
                    synced += 1
            except Exception:
                logger.exception(
                    'Stripe sync failed for professional_subscription_id=%s stripe_subscription_id=%s',
                    subscription.pk,
                    subscription.stripe_subscription_id,
                )
                failed += 1

        level = django_messages.SUCCESS
        if failed:
            level = django_messages.WARNING
        self.message_user(
            request,
            f'Stripe sync complete: {synced} synced, {skipped} skipped, {failed} failed.',
            level,
        )


@admin.register(SubscriptionInvoice)
class SubscriptionInvoiceAdmin(admin.ModelAdmin):
    list_display = ('stripe_invoice_id', 'subscription', 'status', 'amount_due_cents', 'amount_paid_cents', 'paid_at')
    list_filter = ('status', 'currency')
    search_fields = ('stripe_invoice_id', 'subscription__professional__user__email')
    autocomplete_fields = ('subscription',)


@admin.register(BillingWebhookEvent)
class BillingWebhookEventAdmin(admin.ModelAdmin):
    list_display = ('stripe_event_id', 'event_type', 'attempt_count', 'is_processing', 'processed_at', 'received_at')
    list_filter = ('event_type', 'is_processing')
    search_fields = ('stripe_event_id', 'event_type')
