from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import SignUpForm
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
	profile = getattr(request.user, 'professional_profile', None)
	needs_onboarding = (
		request.user.role == User.Role.PROFESSIONAL
		and profile is None
	)
	return render(
		request,
		'accounts/dashboard.html',
		{
			'needs_onboarding': needs_onboarding,
			'profile': profile,
			'service_count': profile.services.count() if profile else 0,
		},
	)
