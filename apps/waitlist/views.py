from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect, render

from .forms import PractitionerWaitlistForm


def waitlist_landing_view(request):
    if request.method == 'POST':
        form = PractitionerWaitlistForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'You are on the practitioner waitlist. We will reach out soon.')
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

    context = {
        'form': form,
        'service_tracks': service_tracks,
    }
    return render(request, 'waitlist/landing.html', context)
