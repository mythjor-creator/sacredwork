from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile

from .forms import ServiceForm
from .models import Category, Service


def marketplace_view(request):
	query = request.GET.get('q', '').strip()
	category_slug = request.GET.get('category', '').strip()

	active_services = Service.objects.filter(is_active=True).select_related('category')
	profiles = (
		ProfessionalProfile.objects.filter(
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		.select_related('user')
		.prefetch_related(Prefetch('services', queryset=active_services))
	)

	if query:
		profiles = profiles.filter(
			Q(user__display_name__icontains=query)
			| Q(user__username__icontains=query)
			| Q(business_name__icontains=query)
			| Q(headline__icontains=query)
			| Q(modalities__icontains=query)
			| Q(services__name__icontains=query)
		)

	if category_slug:
		profiles = profiles.filter(services__category__slug=category_slug)

	context = {
		'profiles': profiles.distinct(),
		'categories': [
			{
				'category': category,
				'selected_attr': ' selected' if category.slug == category_slug else '',
			}
			for category in Category.objects.order_by('name')
		],
		'active_category': category_slug,
		'query': query,
		'sample_badge_text': 'Preview mode: sample data'
		if settings.DEBUG and request.GET.get('sample') == '1'
		else '',
		'sample_badge_style': 'display: inline-block; margin: 0.3rem 0 0.6rem; padding: 0.2rem 0.6rem; border-radius: 999px; border: 1px solid #f59e0b; color: #92400e; background: #fef3c7;'
		if settings.DEBUG and request.GET.get('sample') == '1'
		else 'display: none;',
	}
	return render(request, 'catalog/marketplace_list.html', context)


def home_view(request):
	query = request.GET.get('q', '').strip()
	category_slug = request.GET.get('category', '').strip()
	featured_profiles = (
		ProfessionalProfile.objects.filter(
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		.select_related('user')
		.order_by('user__display_name')[:5]
	)
	context = {
		'query': query,
		'categories': [
			{
				'category': category,
				'selected_attr': ' selected' if category.slug == category_slug else '',
			}
			for category in Category.objects.order_by('name')
		],
		'featured_profiles': featured_profiles,
	}
	return render(request, 'home.html', context)


def professional_detail_view(request, pk):
	profile = get_object_or_404(
		ProfessionalProfile.objects.select_related('user').prefetch_related(
			Prefetch(
				'services',
				queryset=Service.objects.filter(is_active=True).select_related('category'),
			)
		),
		pk=pk,
		approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
		is_visible=True,
	)
	return render(request, 'catalog/professional_detail.html', {'profile': profile})


@login_required
def service_list_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return redirect('professionals:onboarding')

	services = profile.services.select_related('category').order_by('name')
	return render(
		request,
		'catalog/service_list.html',
		{'profile': profile, 'services': services},
	)


@login_required
def service_create_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return redirect('professionals:onboarding')

	if request.method == 'POST':
		form = ServiceForm(request.POST)
		if form.is_valid():
			service = form.save(commit=False)
			service.professional = profile
			service.save()
			return redirect('catalog:service_list')
	else:
		form = ServiceForm()

	return render(
		request,
		'catalog/service_form.html',
		{'form': form, 'profile': profile, 'form_title': 'Add a service'},
	)


@login_required
def service_edit_view(request, pk):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return redirect('professionals:onboarding')

	service = get_object_or_404(Service, pk=pk, professional=profile)

	if request.method == 'POST':
		form = ServiceForm(request.POST, instance=service)
		if form.is_valid():
			form.save()
			return redirect('catalog:service_list')
	else:
		form = ServiceForm(instance=service)

	return render(
		request,
		'catalog/service_form.html',
		{'form': form, 'profile': profile, 'service': service, 'form_title': f'Edit: {service.name}'},
	)
