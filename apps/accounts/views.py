from django.contrib.auth import login
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import AccountSettingsForm, SignUpForm
from .models import User


def _safe_next_url(request):
	next_url = (request.POST.get('next') or request.GET.get('next') or '').strip()
	if next_url and url_has_allowed_host_and_scheme(
		next_url,
		allowed_hosts={request.get_host()},
		require_https=request.is_secure(),
	):
		return next_url
	return ''


class ClairbookLoginView(LoginView):
	template_name = 'accounts/login.html'

	def get_success_url(self):
		next_url = self.get_redirect_url()
		if next_url:
			return next_url
		return reverse('accounts:dashboard')


def signup_view(request):
	if request.user.is_authenticated:
		return redirect('accounts:dashboard')

	next_url = _safe_next_url(request)
	is_booking_flow = 'guest_resume' in next_url

	if request.method == 'POST':
		form = SignUpForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			if next_url:
				return redirect(next_url)
			if user.role == User.Role.PROFESSIONAL:
				return redirect('professionals:onboarding')
			return redirect('accounts:dashboard')
	else:
		form_initial = {}
		if is_booking_flow:
			form_initial['role'] = User.Role.CLIENT
		form = SignUpForm(initial=form_initial)
	return render(request, 'accounts/signup.html', {'form': form, 'next': next_url, 'is_booking_flow': is_booking_flow})


@login_required
def dashboard_view(request):
	if request.user.role == User.Role.PROFESSIONAL:
		profile = getattr(request.user, 'professional_profile', None)
		if profile is None:
			return redirect('professionals:onboarding')
		return redirect('professionals:profile_core')

	return redirect('catalog:marketplace')


@login_required
def account_settings_view(request):
	profile = getattr(request.user, 'professional_profile', None)

	if request.method == 'POST':
		action = request.POST.get('action')
		if action == 'update_profile':
			settings_form = AccountSettingsForm(request.POST, instance=request.user)
			password_form = PasswordChangeForm(request.user)
			if settings_form.is_valid():
				settings_form.save()
				messages.success(request, 'Account details updated.')
				return redirect('accounts:settings')
		elif action == 'change_password':
			settings_form = AccountSettingsForm(instance=request.user)
			password_form = PasswordChangeForm(request.user, request.POST)
			if password_form.is_valid():
				user = password_form.save()
				update_session_auth_hash(request, user)
				messages.success(request, 'Password updated successfully.')
				return redirect('accounts:settings')
		else:
			settings_form = AccountSettingsForm(instance=request.user)
			password_form = PasswordChangeForm(request.user)
	else:
		settings_form = AccountSettingsForm(instance=request.user)
		password_form = PasswordChangeForm(request.user)

	return render(
		request,
		'accounts/settings.html',
		{
			'profile': profile,
			'settings_form': settings_form,
			'password_form': password_form,
		},
	)
