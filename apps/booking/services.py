from datetime import datetime, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from .emails import send_booking_cancelled, send_booking_confirmed, send_booking_requested
from .models import AvailabilityWindow, Booking


ACTIVE_BOOKING_STATUSES = [Booking.Status.REQUESTED, Booking.Status.CONFIRMED]


def generate_service_slots(service, days=14, from_date=None):
	from_date = from_date or timezone.localdate()
	now = timezone.now()
	window_queryset = service.professional.availability_windows.filter(is_active=True).order_by(
		'weekday',
		'start_time',
	)
	bookings = list(
		service.professional.bookings.filter(
			status__in=ACTIVE_BOOKING_STATUSES,
			start_at__date__gte=from_date,
			start_at__date__lte=from_date + timedelta(days=days),
		).order_by('start_at')
	)

	slots = []
	for day_offset in range(days):
		current_date = from_date + timedelta(days=day_offset)
		weekday = current_date.isoweekday()
		for window in window_queryset:
			if window.weekday != weekday:
				continue

			start_dt = timezone.make_aware(datetime.combine(current_date, window.start_time))
			end_dt = timezone.make_aware(datetime.combine(current_date, window.end_time))
			cursor = start_dt
			service_delta = timedelta(minutes=service.duration_minutes)
			while cursor + service_delta <= end_dt:
				slot_end = cursor + service_delta
				if cursor >= now and not _has_conflict(bookings, cursor, slot_end):
					slots.append(
						{
							'start_at': cursor,
							'end_at': slot_end,
							'label': timezone.localtime(cursor).strftime('%a, %b %d at %I:%M %p'),
						}
					)
				cursor += timedelta(minutes=30)

	return slots


def create_booking(client, service, start_at, intake_notes='', send_notification=True):
	end_at = start_at + timedelta(minutes=service.duration_minutes)
	with transaction.atomic():
		active_bookings = service.professional.bookings.select_for_update().filter(
			status__in=ACTIVE_BOOKING_STATUSES,
			start_at__lt=end_at,
			end_at__gt=start_at,
		)
		if active_bookings.exists():
			raise ValueError('That time is no longer available.')
		try:
			booking = Booking.objects.create(
				client=client,
				professional=service.professional,
				service=service,
				start_at=start_at,
				end_at=end_at,
				intake_notes=intake_notes,
				price_cents_snapshot=service.price_cents,
			)
		except IntegrityError as exc:
			raise ValueError('That time is no longer available.') from exc
	if send_notification:
		send_booking_requested(booking)
	return booking


def transition_booking(booking, actor, target_status):
	allowed_targets = {
		Booking.Status.CONFIRMED,
		Booking.Status.CANCELLED,
		Booking.Status.COMPLETED,
	}
	if target_status not in allowed_targets:
		raise ValueError('Unsupported booking transition.')

	with transaction.atomic():
		locked_booking = Booking.objects.select_for_update().select_related(
			'client',
			'professional__user',
		).get(pk=booking.pk)

		if target_status == Booking.Status.CONFIRMED:
			if actor != locked_booking.professional.user:
				raise PermissionError('Only the professional can confirm this booking.')
			if locked_booking.status != Booking.Status.REQUESTED:
				raise ValueError('Only requested bookings can be confirmed.')

		elif target_status == Booking.Status.CANCELLED:
			if actor not in {locked_booking.client, locked_booking.professional.user}:
				raise PermissionError('Only the client or professional can cancel this booking.')
			if locked_booking.status not in {Booking.Status.REQUESTED, Booking.Status.CONFIRMED}:
				raise ValueError('Only requested or confirmed bookings can be cancelled.')

		elif target_status == Booking.Status.COMPLETED:
			if actor != locked_booking.professional.user:
				raise PermissionError('Only the professional can complete this booking.')
			if locked_booking.status != Booking.Status.CONFIRMED:
				raise ValueError('Only confirmed bookings can be completed.')

		locked_booking.status = target_status
		locked_booking.save(update_fields=['status', 'updated_at'])

	if target_status == Booking.Status.CONFIRMED:
		send_booking_confirmed(locked_booking)
	elif target_status == Booking.Status.CANCELLED:
		send_booking_cancelled(locked_booking, cancelled_by=actor)

	return locked_booking


def _has_conflict(bookings, slot_start, slot_end):
	for booking in bookings:
		if booking.start_at < slot_end and booking.end_at > slot_start:
			return True
	return False