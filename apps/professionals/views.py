from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.accounts.models import User

from .forms import CredentialFormSet, GalleryImageFormSet, ProfessionalOnboardingForm
from .models import ProfessionalProfile


def _require_professional_profile(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return None, redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return None, redirect('professionals:onboarding')

	return profile, None


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
			messages.success(request, 'Profile created. Continue your setup below.')
			return redirect('professionals:profile_core')
	else:
		form = ProfessionalOnboardingForm()

	return render(request, 'professionals/onboarding.html', {'form': form})


@login_required
def profile_edit_view(request):
	profile, redirect_response = _require_professional_profile(request)
	if redirect_response is not None:
		return redirect_response

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

	return redirect('professionals:profile_core')


@login_required
def profile_core_view(request):
	profile, redirect_response = _require_professional_profile(request)
	if redirect_response is not None:
		return redirect_response

	if request.method == 'POST':
		form = ProfessionalOnboardingForm(request.POST, request.FILES, instance=profile)
		if form.is_valid():
			form.save()
			messages.success(request, 'Core profile details updated.')
			return redirect('professionals:profile_core')
		edit_mode = True
	else:
		form = ProfessionalOnboardingForm(instance=profile)
		edit_mode = request.GET.get('edit') == '1'

	return render(
		request,
		'professionals/profile_core.html',
		{
			'profile': profile,
			'form': form,
			'edit_mode': edit_mode,
		},
	)


@login_required
def profile_gallery_view(request):
	profile, redirect_response = _require_professional_profile(request)
	if redirect_response is not None:
		return redirect_response

	if request.method == 'POST':
		gallery_formset = GalleryImageFormSet(request.POST, request.FILES, instance=profile, prefix='gallery')
		if gallery_formset.is_valid():
			gallery_formset.save()
			messages.success(request, 'Gallery updated.')
			return redirect('professionals:profile_gallery')
		edit_mode = True
	else:
		gallery_formset = GalleryImageFormSet(instance=profile, prefix='gallery')
		edit_mode = request.GET.get('edit') == '1'

	return render(
		request,
		'professionals/profile_gallery.html',
		{
			'profile': profile,
			'gallery_formset': gallery_formset,
			'edit_mode': edit_mode,
		},
	)


@login_required
def profile_credentials_view(request):
	profile, redirect_response = _require_professional_profile(request)
	if redirect_response is not None:
		return redirect_response

	if request.method == 'POST':
		credential_formset = CredentialFormSet(request.POST, instance=profile, prefix='credentials')
		if credential_formset.is_valid():
			credential_formset.save()
			messages.success(request, 'Credentials updated.')
			return redirect('professionals:profile_credentials')
		edit_mode = True
	else:
		credential_formset = CredentialFormSet(instance=profile, prefix='credentials')
		edit_mode = request.GET.get('edit') == '1'

	return render(
		request,
		'professionals/profile_credentials.html',
		{
			'profile': profile,
			'credential_formset': credential_formset,
			'edit_mode': edit_mode,
		},
	)
