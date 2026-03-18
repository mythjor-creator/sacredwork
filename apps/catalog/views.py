import json
import csv
from urllib.parse import urlencode
from datetime import timedelta

from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.models import User
from apps.professionals.forms import ProfessionalOnboardingForm
from apps.professionals.models import ProfessionalProfile
from apps.waitlist.models import PractitionerWaitlistProfile, StatusTransition

from .forms import ServiceForm, ServiceTierFormSet
from .models import AnalyticsEvent, Category, Service


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
	profile_queryset = ProfessionalProfile.objects.select_related('user').prefetch_related(
		Prefetch(
			'services',
			queryset=Service.objects.filter(is_active=True)
			.select_related('category')
			.prefetch_related('tiers'),
		),
		'gallery_images',
		'credentials',
	)

	is_own_profile = (
		request.user.is_authenticated
		and hasattr(request.user, 'professional_profile')
		and request.user.professional_profile.pk == pk
	)

	if is_own_profile:
		profile = get_object_or_404(profile_queryset, pk=pk)
	else:
		profile = get_object_or_404(
			profile_queryset,
			pk=pk,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)

	if is_own_profile and request.method == 'POST':
		core_form = ProfessionalOnboardingForm(request.POST, request.FILES, instance=profile)
		if core_form.is_valid():
			core_form.save()
			messages.success(request, 'Public profile updated.')
			return redirect('catalog:professional_detail', pk=profile.pk)
	else:
		core_form = ProfessionalOnboardingForm(instance=profile) if is_own_profile else None

	context = {
		'profile': profile,
		'is_own_profile': is_own_profile,
		'core_form': core_form,
	}
	return render(request, 'catalog/professional_detail.html', context)


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
		tier_formset = ServiceTierFormSet(request.POST, prefix='tiers')
		if form.is_valid() and tier_formset.is_valid():
			service = form.save(commit=False)
			service.professional = profile
			service.save()
			tier_formset.instance = service
			tier_formset.save()
			messages.success(request, 'Service created successfully.')
			return redirect('catalog:service_list')
	else:
		form = ServiceForm()
		tier_formset = ServiceTierFormSet(prefix='tiers')

	return render(
		request,
		'catalog/service_form.html',
		{'form': form, 'profile': profile, 'form_title': 'Add a service', 'tier_formset': tier_formset},
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
		tier_formset = ServiceTierFormSet(request.POST, instance=service, prefix='tiers')
		if form.is_valid() and tier_formset.is_valid():
			form.save()
			tier_formset.save()
			messages.success(request, 'Service updated successfully.')
			return redirect('catalog:service_list')
	else:
		form = ServiceForm(instance=service)
		tier_formset = ServiceTierFormSet(instance=service, prefix='tiers')

	return render(
		request,
		'catalog/service_form.html',
		{
			'form': form,
			'profile': profile,
			'service': service,
			'form_title': f'Edit: {service.name}',
			'tier_formset': tier_formset,
		},
	)


@csrf_exempt
@require_POST
def analytics_track_view(request):
	"""Persist lightweight frontend analytics events for KPI reporting."""
	try:
		payload = json.loads(request.body.decode('utf-8'))
	except (json.JSONDecodeError, UnicodeDecodeError):
		return JsonResponse({'ok': False, 'error': 'invalid_payload'}, status=400)

	allowed_events = {'search_submitted', 'profile_viewed', 'waitlist_submitted'}
	event_name = str(payload.get('event', '')).strip()
	if event_name not in allowed_events:
		return JsonResponse({'ok': False, 'error': 'unsupported_event'}, status=400)

	event_payload = payload.get('payload') or {}
	if not isinstance(event_payload, dict):
		event_payload = {}

	profile_id = event_payload.get('profile_id')
	if profile_id not in (None, ''):
		try:
			profile_id = int(profile_id)
		except (TypeError, ValueError):
			profile_id = None
	else:
		profile_id = None

	AnalyticsEvent.objects.create(
		name=event_name,
		source=str(event_payload.get('source', '')).strip()[:40],
		has_query=bool(event_payload.get('has_query')),
		has_category=bool(event_payload.get('has_category')),
		profile_id=profile_id,
		path=str(payload.get('path', '')).strip()[:255],
		user=request.user if request.user.is_authenticated else None,
	)

	return JsonResponse({'ok': True})


@staff_member_required
def analytics_kpi_view(request):
	"""Admin-facing KPI snapshot for recent funnel activity."""
	window_options = [7, 14, 30, 90]
	preset = request.GET.get('preset', '').strip()
	try:
		selected_days = int(request.GET.get('days', '7'))
	except (TypeError, ValueError):
		selected_days = 7
	if selected_days not in window_options:
		selected_days = 7

	now = timezone.now()
	local_now = timezone.localtime(now)
	today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
	this_week_start = today_start - timedelta(days=today_start.weekday())

	if preset == 'this_week':
		window_start = this_week_start
		window_end = now
		window_label = 'This week'
	elif preset == 'last_week':
		window_start = this_week_start - timedelta(days=7)
		window_end = this_week_start
		window_label = 'Last week'
	else:
		preset = ''
		window_start = now - timedelta(days=selected_days)
		window_end = now
		window_label = f'Last {selected_days} days'

	recent_events = AnalyticsEvent.objects.filter(created_at__gte=window_start, created_at__lt=window_end)
	window_duration = window_end - window_start
	previous_window_start = window_start - window_duration
	previous_events = AnalyticsEvent.objects.filter(
		created_at__gte=previous_window_start,
		created_at__lt=window_start,
	)

	search_count = recent_events.filter(name='search_submitted').count()
	profile_count = recent_events.filter(name='profile_viewed').count()
	waitlist_count = recent_events.filter(name='waitlist_submitted').count()
	recent_waitlist_records = PractitionerWaitlistProfile.objects.filter(
		created_at__gte=window_start,
		created_at__lt=window_end,
	).count()

	previous_search_count = previous_events.filter(name='search_submitted').count()
	previous_profile_count = previous_events.filter(name='profile_viewed').count()
	previous_waitlist_count = previous_events.filter(name='waitlist_submitted').count()
	previous_waitlist_records = PractitionerWaitlistProfile.objects.filter(
		created_at__gte=previous_window_start,
		created_at__lt=window_start,
	).count()

	conversion_rate = (waitlist_count / search_count * 100) if search_count else 0

	status_aging_rows = []
	for status_value, status_label in PractitionerWaitlistProfile.Status.choices:
		profiles_in_status = list(
			PractitionerWaitlistProfile.objects.filter(status=status_value).only('status_changed_at')
		)
		count = len(profiles_in_status)
		if count:
			ages_days = [max((now - item.status_changed_at).total_seconds() / 86400, 0) for item in profiles_in_status]
			avg_age_days = round(sum(ages_days) / count, 1)
			oldest_age_days = round(max(ages_days), 1)
		else:
			avg_age_days = 0.0
			oldest_age_days = 0.0
		status_aging_rows.append(
			{
				'status': status_value,
				'label': status_label,
				'count': count,
				'avg_age_days': avg_age_days,
				'oldest_age_days': oldest_age_days,
			}
		)

	# Aggregate status transitions in the window
	transition_rows = []
	for status_value, status_label in PractitionerWaitlistProfile.Status.choices:
		transition_count = StatusTransition.objects.filter(
			to_status=status_value,
			changed_at__gte=window_start,
			changed_at__lt=window_end,
		).count()
		if transition_count > 0:
			transition_rows.append({
				'to_status': status_value,
				'label': status_label,
				'count': transition_count,
			})

	breakdown_rows = (
		recent_events.values('name', 'source')
		.annotate(total=Count('id'))
		.order_by('name', '-total', 'source')
	)
	breakdown_by_name = {
		'search_submitted': [],
		'profile_viewed': [],
		'waitlist_submitted': [],
	}
	for row in breakdown_rows:
		name = row['name']
		if name not in breakdown_by_name:
			continue
		source = row['source'] or 'unknown'
		breakdown_by_name[name].append({'source': source, 'count': row['total']})

	if request.GET.get('format') == 'csv':
		response = HttpResponse(content_type='text/csv')
		window_slug = preset or f'{selected_days}d'
		response['Content-Disposition'] = (
			f'attachment; filename="clairbook-analytics-{window_slug}.csv"'
		)
		writer = csv.writer(response)
		writer.writerow(['metric', 'value'])
		writer.writerow(['window_label', window_label])
		writer.writerow(['window_start', window_start.isoformat()])
		writer.writerow(['window_end', window_end.isoformat()])
		writer.writerow(['search_submitted', search_count])
		writer.writerow(['profile_viewed', profile_count])
		writer.writerow(['waitlist_submitted', waitlist_count])
		writer.writerow(['waitlist_records', recent_waitlist_records])
		writer.writerow(['search_to_waitlist_conversion_pct', round(conversion_rate, 2)])
		writer.writerow([])
		writer.writerow([
			'waitlist_status',
			'count',
			'avg_age_days_since_status_change',
			'oldest_age_days_since_status_change',
		])
		for row in status_aging_rows:
			writer.writerow([row['status'], row['count'], row['avg_age_days'], row['oldest_age_days']])
		writer.writerow([])
		writer.writerow(['status_transitioned_to', 'count'])
		for row in transition_rows:
			writer.writerow([row['to_status'], row['count']])
		writer.writerow([])
		writer.writerow(['event_name', 'source', 'count'])
		for event_name in ['search_submitted', 'profile_viewed', 'waitlist_submitted']:
			for row in breakdown_by_name[event_name]:
				writer.writerow([event_name, row['source'], row['count']])
		writer.writerow([])
		writer.writerow(['event_name', 'source', 'path', 'profile_id', 'user', 'created_at'])
		for event in recent_events.select_related('user')[:5000]:
			writer.writerow(
				[
					event.name,
					event.source,
					event.path,
					event.profile_id or '',
					event.user.username if event.user else '',
					event.created_at.isoformat(),
				]
			)
		return response

	# Pass (value, is_selected) tuples so the template needs no == comparison
	# (formatters tend to strip spaces from {% if x==y %} breaking Django's parser)
	window_options_tagged = [(opt, opt == selected_days) for opt in window_options]
	preset_options_tagged = [
		{'value': 'this_week', 'label': 'This week', 'is_selected': preset == 'this_week'},
		{'value': 'last_week', 'label': 'Last week', 'is_selected': preset == 'last_week'},
	]

	def _delta(current, previous):
		return current - previous

	export_query = {'format': 'csv'}
	if preset:
		export_query['preset'] = preset
	else:
		export_query['days'] = selected_days

	waitlist_admin_url = reverse('admin:waitlist_practitionerwaitlistprofile_changelist')
	profiles_admin_url = reverse('admin:professionals_professionalprofile_changelist')
	ops_shortcuts = [
		{
			'label': 'New waitlist profiles',
			'href': f'{waitlist_admin_url}?status__exact=new',
			'count': PractitionerWaitlistProfile.objects.filter(
				status=PractitionerWaitlistProfile.Status.NEW
			).count(),
		},
		{
			'label': 'Reviewing waitlist profiles',
			'href': f'{waitlist_admin_url}?status__exact=reviewing',
			'count': PractitionerWaitlistProfile.objects.filter(
				status=PractitionerWaitlistProfile.Status.REVIEWING
			).count(),
		},
		{
			'label': 'Invited (not onboarded)',
			'href': f'{waitlist_admin_url}?status__exact=invited',
			'count': PractitionerWaitlistProfile.objects.filter(
				status=PractitionerWaitlistProfile.Status.INVITED
			).count(),
		},
		{
			'label': 'Approved but unverified profiles',
			'href': f'{profiles_admin_url}?approval_status__exact=approved&is_verified__exact=0',
			'count': ProfessionalProfile.objects.filter(
				approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
				is_verified=False,
			).count(),
		},
	]

	context = {
		'window_start': window_start,
		'window_end': window_end,
		'window_label': window_label,
		'selected_days': selected_days,
		'selected_preset': preset,
		'window_options_tagged': window_options_tagged,
		'preset_options_tagged': preset_options_tagged,
		'search_count': search_count,
		'search_delta': _delta(search_count, previous_search_count),
		'profile_count': profile_count,
		'profile_delta': _delta(profile_count, previous_profile_count),
		'waitlist_count': waitlist_count,
		'waitlist_delta': _delta(waitlist_count, previous_waitlist_count),
		'recent_waitlist_records': recent_waitlist_records,
		'waitlist_records_delta': _delta(recent_waitlist_records, previous_waitlist_records),
		'conversion_rate': round(conversion_rate, 2),
		'breakdown_search': breakdown_by_name['search_submitted'],
		'breakdown_profile': breakdown_by_name['profile_viewed'],
		'breakdown_waitlist': breakdown_by_name['waitlist_submitted'],
		'status_aging_rows': status_aging_rows,
		'transition_rows': transition_rows,
		'ops_shortcuts': ops_shortcuts,
		'export_query_string': urlencode(export_query),
		'latest_events': recent_events.select_related('user')[:25],
	}
	return render(request, 'catalog/analytics_kpis.html', context)
