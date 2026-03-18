from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import User

from .forms import CredentialFormSet, GalleryImageFormSet, ProfessionalOnboardingForm
from .models import ProfessionalProfile


@login_required
def onboarding_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is not None:
		return redirect('accounts:dashboard')

	if request.method == 'POST':
		form = ProfessionalOnboardingForm(request.POST, request.FILES)
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
		form = ProfessionalOnboardingForm(request.POST, request.FILES, instance=profile)
		gallery_formset = GalleryImageFormSet(request.POST, request.FILES, instance=profile, prefix='gallery')
		credential_formset = CredentialFormSet(request.POST, instance=profile, prefix='credentials')
		if form.is_valid() and gallery_formset.is_valid() and credential_formset.is_valid():
			form.save()
			gallery_formset.save()
			credential_formset.save()
			messages.success(request, 'Profile updated successfully.')
			return redirect('accounts:dashboard')
	else:
		form = ProfessionalOnboardingForm(instance=profile)
		gallery_formset = GalleryImageFormSet(instance=profile, prefix='gallery')
		credential_formset = CredentialFormSet(instance=profile, prefix='credentials')

	return render(
		request,
		'professionals/profile_edit.html',
		{
			'form': form,
			'profile': profile,
			'gallery_formset': gallery_formset,
			'credential_formset': credential_formset,
			'active_service_count': profile.services.filter(is_active=True).count(),
			'availability_count': profile.availability_windows.filter(is_active=True).count(),
			'in_person_service_count': profile.services.filter(is_active=True).exclude(delivery_format='virtual').count(),
		},
	)
