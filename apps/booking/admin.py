from django.contrib import admin, messages
from django.utils import timezone

from .models import AvailabilityWindow, Booking, BookingPaymentIntent


@admin.register(AvailabilityWindow)
class AvailabilityWindowAdmin(admin.ModelAdmin):
	list_display = ('professional', 'weekday', 'start_time', 'end_time', 'is_active')
	list_filter = ('weekday', 'is_active')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
	list_display = ('service', 'client', 'professional', 'start_at', 'status')
	list_filter = ('status',)
	search_fields = ('service__name', 'client__username', 'professional__business_name')


def mark_refund_resolved(modeladmin, request, queryset):
	"""Mark selected payment intents as refund-resolved (sets flag + timestamp).

	Operators should record the Stripe refund ID (re_...) on each record
	detail page before running this action. Records without a refund_id
	will still be resolved but a warning is shown.
	"""
	needs_refund_id = queryset.filter(requires_manual_refund=True, refund_id='')
	if needs_refund_id.exists():
		missing = ', '.join(f'#{pi.pk}' for pi in needs_refund_id[:5])
		modeladmin.message_user(
			request,
			f'The following records have no Stripe refund ID recorded — enter one in each detail view before resolving: {missing}',
			level=messages.WARNING,
		)

	resolved_count = queryset.filter(requires_manual_refund=True).update(
		requires_manual_refund=False,
		refund_resolved_at=timezone.now(),
	)
	already_clear = queryset.filter(requires_manual_refund=False).count()
	msg = f'{resolved_count} record(s) marked as refund resolved.'
	if already_clear:
		msg += f' {already_clear} record(s) already had no pending refund.'
	modeladmin.message_user(request, msg)


mark_refund_resolved.short_description = 'Mark selected as refund resolved'


@admin.register(BookingPaymentIntent)
class BookingPaymentIntentAdmin(admin.ModelAdmin):
	list_display = (
		'id',
		'client',
		'service',
		'status',
		'requires_manual_refund',
		'refund_id',
		'refund_resolved_at',
		'stripe_payment_intent_id',
		'created_at',
	)
	list_filter = ('status', 'requires_manual_refund', 'created_at')
	search_fields = (
		'client__username',
		'client__email',
		'service__name',
		'stripe_checkout_session_id',
		'stripe_payment_intent_id',
		'refund_id',
	)
	readonly_fields = ('stripe_checkout_session_id', 'stripe_payment_intent_id', 'refund_resolved_at', 'created_at', 'updated_at')
	fields = (
		'client',
		'service',
		'booking',
		'status',
		'start_at',
		'intake_notes',
		'stripe_checkout_session_id',
		'stripe_payment_intent_id',
		'failure_reason',
		'requires_manual_refund',
		'refund_id',
		'refund_resolved_at',
		'created_at',
		'updated_at',
	)
	actions = [mark_refund_resolved]
