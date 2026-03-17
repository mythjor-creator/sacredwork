from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


SITE_NAME = 'Sacred Work'
FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sacredwork.app')


def _fmt_dt(dt):
    local = timezone.localtime(dt)
    return local.strftime('%A, %B %-d at %-I:%M %p')


def send_booking_requested(booking):
    """Notify both parties that a new booking request was made."""
    service_name = booking.service.name
    pro_name = booking.professional.display_name
    client_name = booking.client.display_name or booking.client.username
    when = _fmt_dt(booking.start_at)

    # To client — confirmation of their request
    send_mail(
        subject=f'[{SITE_NAME}] Booking request sent — {service_name}',
        message=(
            f'Hi {client_name},\n\n'
            f'Your booking request for "{service_name}" with {pro_name} on {when} '
            f'has been submitted. You will receive a confirmation email once the '
            f'practitioner reviews and confirms your session.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[booking.client.email],
        fail_silently=True,
    )

    # To professional — new booking to review
    pro_email = booking.professional.user.email
    send_mail(
        subject=f'[{SITE_NAME}] New booking request — {service_name}',
        message=(
            f'Hi {pro_name},\n\n'
            f'You have a new booking request from {client_name} for "{service_name}" '
            f'on {when}.\n\n'
            f'Log in to confirm or cancel this booking.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[pro_email],
        fail_silently=True,
    )


def send_booking_confirmed(booking):
    """Notify the client that the professional confirmed their booking."""
    service_name = booking.service.name
    pro_name = booking.professional.display_name
    client_name = booking.client.display_name or booking.client.username
    when = _fmt_dt(booking.start_at)

    send_mail(
        subject=f'[{SITE_NAME}] Booking confirmed — {service_name}',
        message=(
            f'Hi {client_name},\n\n'
            f'Great news! Your session "{service_name}" with {pro_name} on {when} '
            f'has been confirmed.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[booking.client.email],
        fail_silently=True,
    )


def send_booking_cancelled(booking, cancelled_by):
    """Notify both parties that a booking was cancelled."""
    service_name = booking.service.name
    pro_name = booking.professional.display_name
    client_name = booking.client.display_name or booking.client.username
    when = _fmt_dt(booking.start_at)
    canceller = 'the practitioner' if cancelled_by == booking.professional.user else client_name

    send_mail(
        subject=f'[{SITE_NAME}] Booking cancelled — {service_name}',
        message=(
            f'Hi {client_name},\n\n'
            f'Your booking for "{service_name}" with {pro_name} on {when} '
            f'has been cancelled by {canceller}.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[booking.client.email],
        fail_silently=True,
    )

    pro_email = booking.professional.user.email
    send_mail(
        subject=f'[{SITE_NAME}] Booking cancelled — {service_name}',
        message=(
            f'Hi {pro_name},\n\n'
            f'The booking for "{service_name}" with {client_name} on {when} '
            f'has been cancelled by {canceller}.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[pro_email],
        fail_silently=True,
    )
