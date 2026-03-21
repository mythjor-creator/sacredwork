import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

import stripe

from apps.accounts.models import User

from .payments import (
    available_practitioner_plans,
    create_billing_portal_session,
    create_practitioner_checkout_session,
    default_plan_code_for_profile,
    practitioner_billing_enabled,
    process_billing_webhook,
    resolve_subscription_plan,
)


logger = logging.getLogger(__name__)


@login_required
def billing_overview_view(request):
    if request.user.role != User.Role.PROFESSIONAL:
        return redirect('accounts:dashboard')

    profile = getattr(request.user, 'professional_profile', None)
    if profile is None:
        return redirect('professionals:onboarding')

    subscription = getattr(profile, 'subscription', None)
    selected_plan_code = (request.GET.get('plan') or '').strip() or default_plan_code_for_profile(profile)
    available_plans = available_practitioner_plans()
    try:
        selected_plan = resolve_subscription_plan(selected_plan_code)
    except ValueError:
        selected_plan = available_plans.first()
        selected_plan_code = selected_plan.code if selected_plan else ''

    can_start_checkout = (
        practitioner_billing_enabled()
        and profile.subscription_status
        in {
            profile.SubscriptionStatus.PRELAUNCH,
            profile.SubscriptionStatus.PAST_DUE,
            profile.SubscriptionStatus.CANCELED,
        }
    )
    can_manage_portal = practitioner_billing_enabled() and bool(
        (subscription and subscription.stripe_customer_id) or profile.stripe_customer_id
    )

    return render(
        request,
        'billing/overview.html',
        {
            'profile': profile,
            'subscription': subscription,
            'billing_enabled': practitioner_billing_enabled(),
            'can_start_checkout': can_start_checkout,
            'can_manage_portal': can_manage_portal,
            'available_plans': available_plans,
            'selected_plan': selected_plan,
            'selected_plan_code': selected_plan_code,
        },
    )


@login_required
def billing_checkout_start_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if request.user.role != User.Role.PROFESSIONAL:
        return redirect('accounts:dashboard')

    profile = getattr(request.user, 'professional_profile', None)
    if profile is None:
        return redirect('professionals:onboarding')

    selected_plan_code = (request.POST.get('plan_code') or '').strip() or None

    try:
        checkout_url = create_practitioner_checkout_session(request, profile, plan_code=selected_plan_code)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('billing:overview')

    return redirect(checkout_url)


@login_required
def billing_checkout_success_view(request):
    messages.success(request, 'Checkout completed. Your subscription status will update in a moment.')
    return redirect('billing:overview')


@login_required
def billing_checkout_cancel_view(request):
    messages.warning(request, 'Checkout was canceled. You can restart anytime from billing.')
    return redirect('billing:overview')


@login_required
def billing_portal_start_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    if request.user.role != User.Role.PROFESSIONAL:
        return redirect('accounts:dashboard')

    profile = getattr(request.user, 'professional_profile', None)
    if profile is None:
        return redirect('professionals:onboarding')

    try:
        portal_url = create_billing_portal_session(request, profile)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect('billing:overview')

    return redirect(portal_url)


@csrf_exempt
def stripe_billing_webhook_view(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    signature = request.headers.get('Stripe-Signature', '')
    try:
        process_billing_webhook(request.body, signature)
    except (ValueError, stripe.error.SignatureVerificationError):
        logger.warning('Rejected billing webhook due to invalid payload/signature')
        return HttpResponseBadRequest('Invalid webhook')

    return HttpResponse(status=200)
