from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import User


@login_required
def billing_overview_view(request):
    if request.user.role != User.Role.PROFESSIONAL:
        return redirect('accounts:dashboard')

    profile = getattr(request.user, 'professional_profile', None)
    if profile is None:
        return redirect('professionals:onboarding')

    return render(
        request,
        'billing/overview.html',
        {
            'profile': profile,
            'subscription': getattr(profile, 'subscription', None),
        },
    )
