import logging
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

import stripe

from apps.professionals.models import ProfessionalProfile
from apps.waitlist.models import PractitionerWaitlistProfile

from .models import BillingWebhookEvent, ProfessionalSubscription, SubscriptionInvoice, SubscriptionPlan


logger = logging.getLogger(__name__)


PLAN_PRICE_SETTING_BY_CODE = {
    'basic-monthly': 'STRIPE_PRO_BASIC_PRICE_ID',
    'featured-monthly': 'STRIPE_PRO_FEATURED_PRICE_ID',
    'founding-annual': 'STRIPE_PRO_FOUNDING_PRICE_ID',
}

DEFAULT_PLAN_CODE_BY_TIER = {
    PractitionerWaitlistProfile.SignupTier.FREE: 'basic-monthly',
    PractitionerWaitlistProfile.SignupTier.BASIC: 'basic-monthly',
    PractitionerWaitlistProfile.SignupTier.FEATURED: 'featured-monthly',
    PractitionerWaitlistProfile.SignupTier.FOUNDING: 'founding-annual',
}


def practitioner_billing_enabled() -> bool:
    return bool(getattr(settings, 'PRACTITIONER_BILLING_ENABLED', False))


def available_practitioner_plans():
    return SubscriptionPlan.objects.filter(is_active=True).order_by('display_order', 'amount_cents', 'name')


def default_plan_code_for_profile(profile: ProfessionalProfile) -> str:
    subscription = getattr(profile, 'subscription', None)
    if subscription and subscription.plan_id and subscription.plan and subscription.plan.is_active:
        return subscription.plan.code

    email = (profile.user.email or '').strip()
    if email:
        waitlist_profile = (
            PractitionerWaitlistProfile.objects.filter(email__iexact=email)
            .order_by('-created_at')
            .first()
        )
        if waitlist_profile is not None:
            return DEFAULT_PLAN_CODE_BY_TIER.get(waitlist_profile.signup_tier, 'basic-monthly')

    return 'basic-monthly'


def resolve_subscription_plan(plan_code: str | None) -> SubscriptionPlan:
    normalized_code = (plan_code or '').strip() or 'basic-monthly'
    plan = SubscriptionPlan.objects.filter(code=normalized_code, is_active=True).first()
    if plan is None:
        raise ValueError('Selected billing plan is not configured.')
    return plan


def stripe_price_id_for_plan(plan: SubscriptionPlan) -> str:
    setting_name = PLAN_PRICE_SETTING_BY_CODE.get(plan.code, '')
    if setting_name:
        configured = getattr(settings, setting_name, '').strip()
        if configured:
            return configured
    return (plan.stripe_price_id or '').strip()


def sync_subscription_from_stripe(subscription: ProfessionalSubscription) -> bool:
    stripe_subscription_id = (subscription.stripe_subscription_id or '').strip()
    if not stripe_subscription_id:
        raise ValueError('Subscription has no Stripe subscription id.')

    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        raise ValueError('STRIPE_SECRET_KEY is not configured.')

    stripe_subscription = stripe.Subscription.retrieve(stripe_subscription_id)
    stripe_status = (stripe_subscription.get('status') or '').strip().lower()
    period_end = _parse_stripe_timestamp(stripe_subscription.get('current_period_end'))
    cancel_at_period_end = bool(stripe_subscription.get('cancel_at_period_end'))
    stripe_customer_id = (stripe_subscription.get('customer') or '').strip()

    with transaction.atomic():
        locked = (
            ProfessionalSubscription.objects.select_for_update()
            .select_related('professional')
            .filter(pk=subscription.pk)
            .first()
        )
        if locked is None:
            return False

        locked.status = _map_stripe_subscription_status(stripe_status)
        locked.current_period_end = period_end
        locked.cancel_at_period_end = cancel_at_period_end
        if stripe_customer_id:
            locked.stripe_customer_id = stripe_customer_id
        if locked.status == ProfessionalSubscription.Status.CANCELED and locked.canceled_at is None:
            locked.canceled_at = timezone.now()
        if locked.status != ProfessionalSubscription.Status.CANCELED:
            locked.canceled_at = None
        locked.save(
            update_fields=[
                'status',
                'current_period_end',
                'cancel_at_period_end',
                'stripe_customer_id',
                'canceled_at',
                'updated_at',
            ]
        )

        profile = locked.professional
        profile.subscription_status = _map_profile_subscription_status(locked.status)
        if stripe_customer_id:
            profile.stripe_customer_id = stripe_customer_id
        profile.save(update_fields=['subscription_status', 'stripe_customer_id', 'updated_at'])

    return True


def create_practitioner_checkout_session(request, profile: ProfessionalProfile, *, plan_code: str | None = None) -> str:
    if not practitioner_billing_enabled():
        raise ValueError('Practitioner billing is not enabled.')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    plan = resolve_subscription_plan(plan_code or default_plan_code_for_profile(profile))
    price_id = stripe_price_id_for_plan(plan)
    if not price_id:
        raise ValueError(f'No Stripe price is configured for the {plan.name} plan.')

    subscription, _ = ProfessionalSubscription.objects.get_or_create(
        professional=profile,
        defaults={
            'plan': plan,
            'status': ProfessionalSubscription.Status.PENDING_LAUNCH,
            'founding_member_rate_locked': plan.founding_only,
        },
    )
    if subscription.plan_id != plan.id or subscription.founding_member_rate_locked != plan.founding_only:
        subscription.plan = plan
        subscription.founding_member_rate_locked = plan.founding_only
        subscription.save(update_fields=['plan', 'founding_member_rate_locked', 'updated_at'])

    success_url = request.build_absolute_uri('/billing/checkout/success/')
    cancel_url = request.build_absolute_uri('/billing/checkout/cancel/')

    subscription_data = {}
    if plan.billing_interval == SubscriptionPlan.BillingInterval.MONTH and not plan.founding_only:
        subscription_data['trial_period_days'] = 60

    session = stripe.checkout.Session.create(
        mode='subscription',
        line_items=[{'price': price_id, 'quantity': 1}],
        customer_email=profile.user.email or None,
        metadata={
            'professional_profile_id': str(profile.pk),
            'professional_subscription_id': str(subscription.pk),
            'subscription_plan_code': plan.code,
        },
        success_url=f'{success_url}?session_id={{CHECKOUT_SESSION_ID}}',
        cancel_url=cancel_url,
        subscription_data=subscription_data or None,
    )

    return session.url


def create_billing_portal_session(request, profile: ProfessionalProfile) -> str:
    if not practitioner_billing_enabled():
        raise ValueError('Practitioner billing is not enabled.')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    subscription = getattr(profile, 'subscription', None)
    customer_id = ''
    if subscription is not None:
        customer_id = (subscription.stripe_customer_id or '').strip()
    if not customer_id:
        customer_id = (profile.stripe_customer_id or '').strip()
    if not customer_id:
        raise ValueError('No Stripe customer is connected yet. Complete checkout first.')

    return_url = request.build_absolute_uri('/billing/')
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


def process_billing_webhook(payload, signature_header):
    stripe.api_key = settings.STRIPE_SECRET_KEY
    event = stripe.Webhook.construct_event(
        payload=payload,
        sig_header=signature_header,
        secret=getattr(settings, 'STRIPE_BILLING_WEBHOOK_SECRET', settings.STRIPE_WEBHOOK_SECRET),
    )

    event_type = event.get('type')
    event_object = event.get('data', {}).get('object', {})
    event_id = (event.get('id') or '').strip()

    logger.info('Received billing webhook event=%s id=%s', event_type, event_id)

    webhook_event_id = _acquire_webhook_event(event_id, event_type)
    if event_id and webhook_event_id is None:
        return

    try:
        _dispatch_billing_webhook_event(event_type, event_object, event_id)
    except Exception as exc:
        if webhook_event_id is not None:
            _mark_webhook_event_failed(webhook_event_id, exc)
        raise
    else:
        if webhook_event_id is not None:
            _mark_webhook_event_processed(webhook_event_id)


def _acquire_webhook_event(event_id: str, event_type: str):
    if not event_id:
        return None

    try:
        with transaction.atomic():
            webhook_event, _ = BillingWebhookEvent.objects.select_for_update().get_or_create(
                stripe_event_id=event_id,
                defaults={'event_type': event_type or ''},
            )
            if webhook_event.processed_at is not None:
                logger.info('Skipping duplicate processed billing webhook id=%s type=%s', event_id, event_type)
                return None
            if webhook_event.is_processing:
                logger.info('Skipping in-flight billing webhook id=%s type=%s', event_id, event_type)
                return None

            webhook_event.is_processing = True
            webhook_event.event_type = event_type or webhook_event.event_type
            webhook_event.attempt_count += 1
            webhook_event.last_error = ''
            webhook_event.save(update_fields=['is_processing', 'event_type', 'attempt_count', 'last_error', 'updated_at'])
            return webhook_event.pk
    except IntegrityError:
        logger.info('Skipping duplicate billing webhook due to race id=%s type=%s', event_id, event_type)
        return None


def _mark_webhook_event_processed(webhook_event_id: int):
    BillingWebhookEvent.objects.filter(pk=webhook_event_id).update(
        is_processing=False,
        processed_at=timezone.now(),
        last_error='',
    )


def _mark_webhook_event_failed(webhook_event_id: int, exc: Exception):
    BillingWebhookEvent.objects.filter(pk=webhook_event_id).update(
        is_processing=False,
        last_error=str(exc)[:500],
    )


def _dispatch_billing_webhook_event(event_type, event_object, event_id):

    if event_type == 'checkout.session.completed':
        _handle_checkout_completed(event_object)
    elif event_type in {'customer.subscription.updated', 'customer.subscription.deleted'}:
        _handle_subscription_updated(event_object)
    elif event_type == 'invoice.paid':
        _handle_invoice_paid(event_object)
    elif event_type == 'invoice.payment_failed':
        _handle_invoice_payment_failed(event_object)
    else:
        logger.info('Ignoring unsupported billing webhook event=%s id=%s', event_type, event_id)


def _handle_checkout_completed(session):
    metadata = session.get('metadata') or {}
    subscription_id = metadata.get('professional_subscription_id')
    profile_id = metadata.get('professional_profile_id')
    plan_code = (metadata.get('subscription_plan_code') or '').strip()
    stripe_subscription_id = session.get('subscription') or ''
    stripe_customer_id = session.get('customer') or ''

    if not subscription_id or not profile_id:
        return

    with transaction.atomic():
        subscription = ProfessionalSubscription.objects.select_for_update().filter(pk=subscription_id).first()
        profile = ProfessionalProfile.objects.select_for_update().filter(pk=profile_id).first()
        if subscription is None or profile is None:
            return

        selected_plan = SubscriptionPlan.objects.filter(code=plan_code).first() if plan_code else None

        subscription.status = ProfessionalSubscription.Status.ACTIVE
        subscription.stripe_subscription_id = stripe_subscription_id or subscription.stripe_subscription_id
        subscription.stripe_customer_id = stripe_customer_id or subscription.stripe_customer_id
        if selected_plan is not None:
            subscription.plan = selected_plan
            subscription.founding_member_rate_locked = selected_plan.founding_only
        if subscription.activated_at is None:
            subscription.activated_at = timezone.now()
        subscription.save(
            update_fields=[
                'status',
                'stripe_subscription_id',
                'stripe_customer_id',
                'plan',
                'founding_member_rate_locked',
                'activated_at',
                'updated_at',
            ]
        )

        profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        if stripe_customer_id:
            profile.stripe_customer_id = stripe_customer_id
        profile.subscription_fails_count = 0
        profile.save(update_fields=['subscription_status', 'stripe_customer_id', 'subscription_fails_count', 'updated_at'])


def _handle_subscription_updated(subscription_event):
    stripe_subscription_id = subscription_event.get('id')
    if not stripe_subscription_id:
        return

    stripe_status = (subscription_event.get('status') or '').strip().lower()
    period_end = _parse_stripe_timestamp(subscription_event.get('current_period_end'))
    cancel_at_period_end = bool(subscription_event.get('cancel_at_period_end'))

    with transaction.atomic():
        subscription = (
            ProfessionalSubscription.objects.select_for_update()
            .select_related('professional')
            .filter(stripe_subscription_id=stripe_subscription_id)
            .first()
        )
        if subscription is None:
            return

        previous_subscription_status = subscription.status
        subscription.status = _map_stripe_subscription_status(stripe_status)
        subscription.current_period_end = period_end
        subscription.cancel_at_period_end = cancel_at_period_end
        if subscription.status == ProfessionalSubscription.Status.CANCELED and subscription.canceled_at is None:
            subscription.canceled_at = timezone.now()
        if subscription.status != ProfessionalSubscription.Status.CANCELED:
            subscription.canceled_at = None
        subscription.save(
            update_fields=[
                'status',
                'current_period_end',
                'cancel_at_period_end',
                'canceled_at',
                'updated_at',
            ]
        )

        profile = subscription.professional
        profile.subscription_status = _map_profile_subscription_status(subscription.status)
        if (
            subscription.status == ProfessionalSubscription.Status.PAST_DUE
            and previous_subscription_status != ProfessionalSubscription.Status.PAST_DUE
        ):
            profile.subscription_fails_count += 1
        if subscription.status == ProfessionalSubscription.Status.ACTIVE:
            profile.subscription_fails_count = 0
        profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])


def _handle_invoice_paid(invoice_event):
    stripe_invoice_id = (invoice_event.get('id') or '').strip()
    stripe_subscription_id = (invoice_event.get('subscription') or '').strip()
    if not stripe_invoice_id or not stripe_subscription_id:
        return

    with transaction.atomic():
        subscription = (
            ProfessionalSubscription.objects.select_for_update()
            .select_related('professional')
            .filter(stripe_subscription_id=stripe_subscription_id)
            .first()
        )
        if subscription is None:
            return

        _upsert_invoice(invoice_event, subscription, SubscriptionInvoice.Status.PAID)

        subscription.status = ProfessionalSubscription.Status.ACTIVE
        subscription.save(update_fields=['status', 'updated_at'])

        profile = subscription.professional
        profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        profile.subscription_fails_count = 0
        profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])


def _handle_invoice_payment_failed(invoice_event):
    stripe_invoice_id = (invoice_event.get('id') or '').strip()
    stripe_subscription_id = (invoice_event.get('subscription') or '').strip()
    if not stripe_invoice_id or not stripe_subscription_id:
        return

    with transaction.atomic():
        subscription = (
            ProfessionalSubscription.objects.select_for_update()
            .select_related('professional')
            .filter(stripe_subscription_id=stripe_subscription_id)
            .first()
        )
        if subscription is None:
            return

        _, created, previous_invoice_status = _upsert_invoice(
            invoice_event,
            subscription,
            SubscriptionInvoice.Status.OPEN,
        )

        subscription.status = ProfessionalSubscription.Status.PAST_DUE
        subscription.save(update_fields=['status', 'updated_at'])

        profile = subscription.professional
        profile.subscription_status = ProfessionalProfile.SubscriptionStatus.PAST_DUE
        if created or previous_invoice_status != SubscriptionInvoice.Status.OPEN:
            profile.subscription_fails_count += 1
        profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])


def _upsert_invoice(invoice_event, subscription, status_override=None):
    stripe_invoice_id = (invoice_event.get('id') or '').strip()
    if not stripe_invoice_id:
        return None, False, None

    raw_status = (invoice_event.get('status') or '').strip().lower()
    status = status_override if status_override is not None else (raw_status or SubscriptionInvoice.Status.DRAFT)

    paid_at = None
    status_transitions = invoice_event.get('status_transitions') or {}
    if status_transitions.get('paid_at'):
        paid_at = _parse_stripe_timestamp(status_transitions['paid_at'])

    existing_invoice = SubscriptionInvoice.objects.filter(stripe_invoice_id=stripe_invoice_id).first()
    previous_status = existing_invoice.status if existing_invoice is not None else None

    invoice, created = SubscriptionInvoice.objects.update_or_create(
        stripe_invoice_id=stripe_invoice_id,
        defaults={
            'subscription': subscription,
            'status': status,
            'amount_due_cents': invoice_event.get('amount_due') or 0,
            'amount_paid_cents': invoice_event.get('amount_paid') or 0,
            'currency': (invoice_event.get('currency') or 'usd').lower(),
            'hosted_invoice_url': (invoice_event.get('hosted_invoice_url') or '').strip(),
            'paid_at': paid_at,
        },
    )
    return invoice, created, previous_status


def _map_stripe_subscription_status(stripe_status: str) -> str:
    if stripe_status in {'active', 'trialing'}:
        return ProfessionalSubscription.Status.ACTIVE
    if stripe_status in {'past_due', 'incomplete', 'incomplete_expired', 'unpaid'}:
        return ProfessionalSubscription.Status.PAST_DUE
    if stripe_status in {'canceled'}:
        return ProfessionalSubscription.Status.CANCELED
    return ProfessionalSubscription.Status.PENDING_LAUNCH


def _map_profile_subscription_status(subscription_status: str) -> str:
    if subscription_status == ProfessionalSubscription.Status.ACTIVE:
        return ProfessionalProfile.SubscriptionStatus.ACTIVE
    if subscription_status == ProfessionalSubscription.Status.PAST_DUE:
        return ProfessionalProfile.SubscriptionStatus.PAST_DUE
    if subscription_status == ProfessionalSubscription.Status.CANCELED:
        return ProfessionalProfile.SubscriptionStatus.CANCELED
    return ProfessionalProfile.SubscriptionStatus.PRELAUNCH


def _parse_stripe_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=dt_timezone.utc)
    except (TypeError, ValueError, OSError):
        return None
