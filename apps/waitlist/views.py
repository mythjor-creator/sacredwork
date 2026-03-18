from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect, render

from .emails import send_waitlist_confirmation
from .forms import PractitionerWaitlistForm
from .models import PractitionerWaitlistProfile


def waitlist_landing_view(request):
    if request.method == 'POST':
        form = PractitionerWaitlistForm(request.POST)
        if form.is_valid():
            profile = form.save()
            send_waitlist_confirmation(profile)
            messages.success(request, 'You are on the waitlist. We will reach out soon.')
            return redirect(f"{reverse('waitlist:landing')}?submitted=1")
    else:
        form = PractitionerWaitlistForm()

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
    }
    return render(request, 'waitlist/landing.html', context)
