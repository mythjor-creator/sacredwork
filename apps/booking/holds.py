"""Utilities for managing booking slot holds."""

from datetime import timedelta
from django.utils import timezone
from .models import BookingHold


HOLD_DURATION_MINUTES = 15


def acquire_hold(client, professional, service, start_at):
	"""
	Acquire a hold on a slot for a client.
	
	Raises IntegrityError if the slot is already held.
	"""
	expires_at = timezone.now() + timedelta(minutes=HOLD_DURATION_MINUTES)
	hold = BookingHold.objects.create(
		client=client,
		professional=professional,
		service=service,
		start_at=start_at,
		expires_at=expires_at,
	)
	return hold


def release_hold(professional, start_at):
	"""Release any active hold on a slot."""
	BookingHold.objects.filter(
		professional=professional,
		start_at=start_at,
	).delete()


def cleanup_expired_holds():
	"""Delete all expired holds."""
	now = timezone.now()
	BookingHold.objects.filter(expires_at__lte=now).delete()


def slot_is_available(professional, start_at):
	"""Check if a slot is available (not held and not booked)."""
	from .models import Booking
	
	# Check for active hold
	hold_exists = BookingHold.objects.filter(
		professional=professional,
		start_at=start_at,
	).exists()
	
	if hold_exists:
		return False
	
	# Check for existing booking
	booking_exists = Booking.objects.filter(
		professional=professional,
		start_at=start_at,
	).exists()
	
	return not booking_exists
