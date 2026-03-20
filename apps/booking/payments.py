from django.conf import settings
from django.db import transaction
from django.urls import reverse

import stripe

from .models import BookingPaymentIntent
from .services import create_booking
from .emails import send_booking_payment_received
from .holds import release_hold


def payment_gateway_enabled() -> bool:
    return bool(getattr(settings, 'STRIPE_SECRET_KEY', '').strip())


def create_booking_checkout_session(request, *, client, service, start_at, intake_notes=''):
    intent = BookingPaymentIntent.objects.create(
        client=client,
        service=service,
        start_at=start_at,
        intake_notes=intake_notes,
    )

    return create_checkout_session_for_intent(request, intent)


def create_checkout_session_for_intent(request, intent):
    service = intent.service
    start_at = intent.start_at

    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = request.build_absolute_uri(reverse('booking:payment_success'))
    cancel_url = request.build_absolute_uri(reverse('booking:payment_cancel'))

    session = stripe.checkout.Session.create(
        mode='payment',
        line_items=[
            {
                'price_data': {
                    'currency': getattr(settings, 'STRIPE_CURRENCY', 'usd'),
                    'product_data': {
                        'name': f'{service.name} with {service.professional.display_name}',
                        'description': f'Booking on {start_at.isoformat()}',
                    },
                    'unit_amount': service.price_cents,
                },
                'quantity': 1,
            }
        ],
        customer_email=intent.client.email or None,
        metadata={'booking_payment_intent_id': str(intent.pk)},
        client_reference_id=str(intent.pk),
        success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
        cancel_url=cancel_url,
    )

    intent.status = BookingPaymentIntent.Status.PENDING
    intent.stripe_checkout_session_id = session.id
    intent.failure_reason = ''
    intent.requires_manual_refund = False
    intent.save(
        update_fields=[
            'status',
            'stripe_checkout_session_id',
            'failure_reason',
            'requires_manual_refund',
            'updated_at',
        ]
    )
    return session.url


def process_stripe_webhook(payload, signature_header):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature_header,
        secret=settings.STRIPE_WEBHOOK_SECRET,
    )

    event_type = event.get('type')
    if event_type == 'checkout.session.completed':
        _complete_checkout_session(event['data']['object'])
    elif event_type == 'checkout.session.expired':
        _expire_checkout_session(event['data']['object'])


def _complete_checkout_session(session):
    intent_id = _session_intent_id(session)
    if not intent_id:
        return

    booking_created = None

    with transaction.atomic():
        intent = BookingPaymentIntent.objects.select_for_update().select_related(
            'client',
            'service__professional',
        ).get(pk=intent_id)

        if intent.status == BookingPaymentIntent.Status.COMPLETED:
            return

        intent.stripe_payment_intent_id = session.get('payment_intent') or ''

        try:
            booking = create_booking(
                client=intent.client,
                service=intent.service,
                start_at=intent.start_at,
                intake_notes=intent.intake_notes,
                send_notification=False,
            )
        except ValueError:
            intent.status = BookingPaymentIntent.Status.FAILED
            intent.failure_reason = 'Slot became unavailable after successful payment.'
            intent.requires_manual_refund = True
            intent.save(
                update_fields=[
                    'status',
                    'failure_reason',
                    'requires_manual_refund',
                    'stripe_payment_intent_id',
                    'updated_at',
                ]
            )
            return

        intent.booking = booking
        intent.status = BookingPaymentIntent.Status.COMPLETED
        intent.failure_reason = ''
        intent.requires_manual_refund = False
        intent.save(
            update_fields=[
                'booking',
                'status',
                'failure_reason',
                'requires_manual_refund',
                'stripe_payment_intent_id',
                'updated_at',
            ]
        )
        booking_created = booking
        # Release hold now that booking is confirmed
        release_hold(intent.service.professional, intent.start_at)

    if booking_created is not None:
        send_booking_payment_received(booking_created)


def _expire_checkout_session(session):
    intent_id = _session_intent_id(session)
    if not intent_id:
        return

    intent = BookingPaymentIntent.objects.select_related('service__professional').get(pk=intent_id)
    release_hold(intent.service.professional, intent.start_at)
    
    BookingPaymentIntent.objects.filter(
        pk=intent_id,
        status=BookingPaymentIntent.Status.PENDING,
    ).update(status=BookingPaymentIntent.Status.EXPIRED)


def _session_intent_id(session):
    metadata = session.get('metadata') or {}
    value = metadata.get('booking_payment_intent_id') or session.get('client_reference_id')
    if not value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
