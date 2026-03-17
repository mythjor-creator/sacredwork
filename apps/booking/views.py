from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import User
from apps.catalog.models import Service

from .forms import AvailabilityWindowForm, BookingRequestForm
from .models import AvailabilityWindow, Booking
from .services import create_booking, generate_service_slots, transition_booking


@login_required
def availability_list_view(request):
	if request.user.role != User.Role.PROFESSIONAL:
		return redirect('accounts:dashboard')

	profile = getattr(request.user, 'professional_profile', None)
	if profile is None:
		return redirect('professionals:onboarding')

	if request.method == 'POST':
		form = AvailabilityWindowForm(request.POST)
		if form.is_valid():
			window = form.save(commit=False)
			window.professional = profile
			window.save()
			return redirect('booking:availability')
	else:
		form = AvailabilityWindowForm()

	availability_windows = profile.availability_windows.order_by('weekday', 'start_time')
	return render(
		request,
		'booking/availability_list.html',
		{
			'form': form,
			'profile': profile,
			'availability_windows': availability_windows,
		},
	)


@login_required
def booking_create_view(request, service_id):
	service = get_object_or_404(
		Service.objects.select_related('professional', 'category'),
		pk=service_id,
		is_active=True,
		professional__approval_status='approved',
		professional__is_visible=True,
	)

	if request.user.role != User.Role.CLIENT:
		return redirect('accounts:dashboard')

	slots = generate_service_slots(service)
	if request.method == 'POST':
		form = BookingRequestForm(request.POST, slots=slots)
		if form.is_valid():
			try:
				create_booking(
					client=request.user,
					service=service,
					start_at=form.cleaned_data['start_at'],
					intake_notes=form.cleaned_data['intake_notes'],
				)
				return redirect('booking:list')
			except ValueError as exc:
				form.add_error('slot', str(exc))
	else:
		form = BookingRequestForm(slots=slots)

	return render(
		request,
		'booking/booking_form.html',
		{
			'form': form,
			'service': service,
			'profile': service.professional,
			'slots': slots,
		},
	)


@login_required
def booking_list_view(request):
	if request.user.role == User.Role.PROFESSIONAL:
		profile = getattr(request.user, 'professional_profile', None)
		bookings = (
			profile.bookings.select_related('client', 'service').order_by('start_at')
			if profile is not None
			else Booking.objects.none()
		)
		view_type = 'professional'
	else:
		bookings = request.user.client_bookings.select_related('professional', 'service').order_by('start_at')
		view_type = 'client'

	return render(
		request,
		'booking/booking_list.html',
		{'bookings': bookings, 'view_type': view_type, 'today': timezone.now()},
	)


@login_required
@require_POST
def booking_action_view(request, booking_id, action):
	booking = get_object_or_404(
		Booking.objects.select_related('client', 'professional__user', 'service'),
		pk=booking_id,
	)

	action_map = {
		'confirm': Booking.Status.CONFIRMED,
		'cancel': Booking.Status.CANCELLED,
		'complete': Booking.Status.COMPLETED,
	}
	target_status = action_map.get(action)
	if target_status is None:
		return redirect('booking:list')

	try:
		transition_booking(booking, request.user, target_status)
		messages.success(request, f'Booking {target_status} successfully.')
	except PermissionError as exc:
		messages.error(request, str(exc))
	except ValueError as exc:
		messages.error(request, str(exc))

	return redirect('booking:list')
