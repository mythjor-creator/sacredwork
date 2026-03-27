from .forms import SimpleWaitlistForm
# --- Minimal public waitlist signup ---
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def simple_waitlist_signup(request):
    if request.method == 'POST':
        form = SimpleWaitlistForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.status = PractitionerWaitlistProfile.Status.NEW
            profile.save()
            return render(request, 'waitlist/success.html', {'profile': profile})
    else:
        form = SimpleWaitlistForm()
    return render(request, 'waitlist/simple_signup.html', {'form': form})
import logging
from threading import Thread

from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect, render

from .emails import send_waitlist_confirmation
from .forms import PractitionerWaitlistForm
from .models import PractitionerWaitlistProfile


logger = logging.getLogger(__name__)


def _send_waitlist_confirmation_background(profile):
    try:
        send_waitlist_confirmation(profile)
    except Exception:
        logger.exception('Waitlist confirmation email failed for profile_id=%s', profile.id)


def waitlist_landing_view(request):
    valid_tiers = {
        PractitionerWaitlistProfile.SignupTier.FREE,
        PractitionerWaitlistProfile.SignupTier.BASIC,
        PractitionerWaitlistProfile.SignupTier.FEATURED,
        PractitionerWaitlistProfile.SignupTier.FOUNDING,
    }

    requested_tier = request.GET.get('tier', '').strip().lower()
    if requested_tier not in valid_tiers:
        requested_tier = PractitionerWaitlistProfile.SignupTier.FREE

    if request.GET.get('founding') == '1':
        requested_tier = PractitionerWaitlistProfile.SignupTier.FOUNDING

    if request.method == 'POST':
        form = PractitionerWaitlistForm(request.POST)
        if form.is_valid():
            profile = form.save()
            if getattr(settings, 'WAITLIST_CONFIRMATION_EMAIL_ASYNC', False):
                Thread(
                    target=_send_waitlist_confirmation_background,
                    args=(profile,),
                    daemon=True,
                ).start()
                messages.success(request, 'You are on the waitlist. We will reach out soon.')
            else:
                try:
                    send_waitlist_confirmation(profile)
                except Exception:
                    logger.exception('Waitlist confirmation email failed for profile_id=%s', profile.id)
                    messages.warning(
                        request,
                        'You are on the waitlist, but we could not send your confirmation email right now. '
                        'Please check your address and try again shortly.',
                    )
                else:
                    messages.success(request, 'You are on the waitlist. We will reach out soon.')
            return redirect(f"{reverse('waitlist:landing')}?submitted=1")
    else:
        is_founding = requested_tier == PractitionerWaitlistProfile.SignupTier.FOUNDING
        form = PractitionerWaitlistForm(
            initial={
                'is_founding_member': is_founding,
                'signup_tier': requested_tier,
            }
        )

    service_tracks = [
        {
            'title': 'Wellness Practitioners',
            'description': 'Yoga, somatic work, mindfulness, nutrition, and holistic care offerings.',
        },
        {
            'title': 'Spiritual Guides',
            'description': 'Energy work, meditation mentorship, astrology, and ceremonial support.',
        },
        {
            'title': 'Beauty and Ritual',
            'description': 'Practices that blend beauty, confidence, and intentional self-care.',
        },
        {
            'title': 'Coaching Practices',
            'description': 'Relationship, career, leadership, and transformational coaching services.',
        },
    ]

    practitioner_benefits = [
        {
            'title': 'Early visibility and category positioning',
            'description': 'Launch cohort practitioners are featured first while client discovery behavior is still forming.',
        },
        {
            'title': 'Input on profile and booking UX',
            'description': 'Your feedback helps shape how services, tiers, and trust signals are shown to clients.',
        },
        {
            'title': 'Invitation-based onboarding support',
            'description': 'Invited practices receive guided setup for profile quality, services, and availability.',
        },
    ]

    approval_flow = [
        {
            'status': PractitionerWaitlistProfile.Status.NEW,
            'title': 'New',
            'description': 'Your application is received and queued for review.',
        },
        {
            'status': PractitionerWaitlistProfile.Status.REVIEWING,
            'title': 'Reviewing',
            'description': 'We evaluate practice fit, service clarity, and launch category balance.',
        },
        {
            'status': PractitionerWaitlistProfile.Status.INVITED,
            'title': 'Invited',
            'description': 'You receive an invite email and move into guided onboarding.',
        },
        {
            'status': PractitionerWaitlistProfile.Status.ONBOARDED,
            'title': 'Onboarded',
            'description': 'Your setup is complete and your profile is ready for launch visibility.',
        },
    ]

    context = {
        'form': form,
        'service_tracks': service_tracks,
        'practitioner_benefits': practitioner_benefits,
        'approval_flow': approval_flow,
        'site_base_url': request.build_absolute_uri('/').rstrip('/'),
        'current_absolute_url': request.build_absolute_uri(),
        'requested_tier': requested_tier,
    }
    return render(request, 'waitlist/landing.html', context)
