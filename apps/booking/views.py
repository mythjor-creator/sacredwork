from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

import stripe

from apps.accounts.models import User
from apps.catalog.models import Service

from .forms import AvailabilityWindowForm, BookingRequestForm
from .models import AvailabilityWindow, Booking, BookingPaymentIntent
from .payments import (
	create_booking_checkout_session,
	create_checkout_session_for_intent,
	payment_gateway_enabled,
	process_stripe_webhook,
)
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
				if payment_gateway_enabled():
					checkout_url = create_booking_checkout_session(
						request,
						client=request.user,
						service=service,
						start_at=form.cleaned_data['start_at'],
						intake_notes=form.cleaned_data['intake_notes'],
					)
					return redirect(checkout_url)

				if settings.BOOKING_REQUIRE_PAYMENT:
					form.add_error(None, 'Payments are temporarily unavailable. Please try again shortly.')
				else:
					create_booking(
						client=request.user,
						service=service,
						start_at=form.cleaned_data['start_at'],
						intake_notes=form.cleaned_data['intake_notes'],
					)
					messages.warning(
						request,
						'Payment gateway is not configured; booking request was created without payment.',
					)
					return redirect('booking:list')
			except ValueError as exc:
				form.add_error('slot', str(exc))
			except stripe.error.StripeError:
				form.add_error(None, 'We could not start checkout. Please try again.')
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
			'payments_enabled': payment_gateway_enabled(),
		},
	)


@login_required
def booking_list_view(request):
	pending_payment_intents = BookingPaymentIntent.objects.none()
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
		pending_payment_intents = request.user.booking_payment_intents.select_related(
			'service__professional'
		).filter(
			booking__isnull=True,
			status__in=[
				BookingPaymentIntent.Status.PENDING,
				BookingPaymentIntent.Status.FAILED,
				BookingPaymentIntent.Status.EXPIRED,
			],
		)
		view_type = 'client'

	return render(
		request,
		'booking/booking_list.html',
		{
			'bookings': bookings,
			'pending_payment_intents': pending_payment_intents,
			'view_type': view_type,
			'today': timezone.now(),
		},
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


@login_required
def booking_payment_success_view(request):
	session_id = request.GET.get('session_id', '').strip()
	if session_id:
		intent = BookingPaymentIntent.objects.filter(stripe_checkout_session_id=session_id).first()
		if intent and intent.status == BookingPaymentIntent.Status.COMPLETED:
			messages.success(request, 'Payment received. Your booking request has been submitted.')
		elif intent and intent.status == BookingPaymentIntent.Status.FAILED:
			messages.error(
				request,
				'Payment succeeded, but that slot was just taken. Please pick a different time and contact support for help.',
			)
		else:
			messages.info(request, 'Payment is processing. We will refresh your booking list shortly.')
	else:
		messages.info(request, 'Checkout completed. We are finalizing your booking now.')

	return redirect('booking:list')


@login_required
@require_POST
def booking_payment_retry_view(request, intent_id):
	if request.user.role != User.Role.CLIENT:
		return redirect('accounts:dashboard')

	intent = get_object_or_404(
		BookingPaymentIntent.objects.select_related('service__professional'),
		pk=intent_id,
		client=request.user,
		booking__isnull=True,
	)
	if intent.status not in {
		BookingPaymentIntent.Status.PENDING,
		BookingPaymentIntent.Status.FAILED,
		BookingPaymentIntent.Status.EXPIRED,
	}:
		messages.error(request, 'This payment cannot be retried.')
		return redirect('booking:list')

	if not payment_gateway_enabled():
		messages.error(request, 'Payments are not configured right now.')
		return redirect('booking:list')

	try:
		checkout_url = create_checkout_session_for_intent(request, intent)
	except stripe.error.StripeError:
		messages.error(request, 'We could not start checkout. Please try again.')
		return redirect('booking:list')

	return redirect(checkout_url)


@login_required
def booking_payment_cancel_view(request):
	messages.info(request, 'Checkout was canceled. No payment was captured.')
	return redirect('booking:list')


@csrf_exempt
@require_POST
def stripe_webhook_view(request):
	if not payment_gateway_enabled() or not settings.STRIPE_WEBHOOK_SECRET:
		return HttpResponseBadRequest('Stripe webhook is not configured.')

	signature = request.META.get('HTTP_STRIPE_SIGNATURE', '')
	try:
		process_stripe_webhook(request.body, signature)
	except stripe.error.SignatureVerificationError:
		return HttpResponseBadRequest('Invalid signature.')
	except ValueError:
		return HttpResponseBadRequest('Invalid payload.')

	return HttpResponse('ok')
