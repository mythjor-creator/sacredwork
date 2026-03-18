from django.contrib.auth import login
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import AccountSettingsForm, SignUpForm
from .models import User


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

	if request.method == 'POST':
		form = SignUpForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			if user.role == User.Role.PROFESSIONAL:
				return redirect('professionals:onboarding')
			return redirect('accounts:dashboard')
	else:
		form = SignUpForm()
	return render(request, 'accounts/signup.html', {'form': form})


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
