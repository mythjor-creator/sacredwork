from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import User

from .forms import ProfessionalOnboardingForm
from .models import ProfessionalProfile


@login_required
def onboarding_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is not None:
		return redirect('accounts:dashboard')

	if request.method == 'POST':
		form = ProfessionalOnboardingForm(request.POST)
		if form.is_valid():
			profile = form.save(commit=False)
			profile.user = request.user
			profile.approval_status = ProfessionalProfile.ApprovalStatus.PENDING
			profile.is_visible = False
			profile.save()
			return redirect('accounts:dashboard')
	else:
		form = ProfessionalOnboardingForm()

	return render(request, 'professionals/onboarding.html', {'form': form})


@login_required
def profile_edit_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return redirect('professionals:onboarding')

	if request.method == 'POST':
		form = ProfessionalOnboardingForm(request.POST, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, 'Profile updated successfully.')
			return redirect('accounts:dashboard')
	else:
		form = ProfessionalOnboardingForm(instance=profile)

	return render(request, 'professionals/profile_edit.html', {'form': form, 'profile': profile})
