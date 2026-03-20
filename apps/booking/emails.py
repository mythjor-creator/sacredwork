from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone


SITE_NAME = 'clairbook'
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


def send_booking_payment_received(booking):
    """
    Notify both parties after a Stripe payment succeeds and the booking is created.

    Uses distinct copy from send_booking_requested() because the client has already
    paid — the message should confirm the payment, not just the request submission.
    """
    service_name = booking.service.name
    pro_name = booking.professional.display_name
    client_name = booking.client.display_name or booking.client.username
    when = _fmt_dt(booking.start_at)
    amount = f'${booking.price_cents_snapshot / 100:.2f}'

    # To client — payment receipt + booking submitted
    send_mail(
        subject=f'[{SITE_NAME}] Payment received — {service_name}',
        message=(
            f'Hi {client_name},\n\n'
            f'Your payment of {amount} for "{service_name}" with {pro_name} on {when} '
            f'has been received. Your booking request has been submitted and you will '
            f'receive a confirmation email once {pro_name} reviews your session.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[booking.client.email],
        fail_silently=True,
    )

    # To professional — paid booking ready to confirm
    pro_email = booking.professional.user.email
    send_mail(
        subject=f'[{SITE_NAME}] New paid booking — {service_name}',
        message=(
            f'Hi {pro_name},\n\n'
            f'You have a new paid booking from {client_name} for "{service_name}" '
            f'on {when}. Payment of {amount} has been collected.\n\n'
            f'Log in to confirm or cancel this booking.\n\n'
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[pro_email],
        fail_silently=True,
    )
