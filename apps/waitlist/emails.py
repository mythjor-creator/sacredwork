from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

SITE_NAME = 'clairbook'
FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sacredwork.app')
SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000')


def send_waitlist_confirmation(profile):
    """Send email verification link to a practitioner who just joined the waitlist."""
    from apps.pages.models import EmailVerificationToken
    
    # Create verification token
    token = EmailVerificationToken.create_for_profile(profile)
    
    verification_url = f"{SITE_URL}{reverse('pages:verify_email', args=[token.token])}"
    
    send_mail(
        subject=f"[{SITE_NAME}] Verify your email to complete your application",
        message=(
            f'Hi {profile.full_name},\n\n'
            f"Thanks for joining the {SITE_NAME} practitioner waitlist! "
            f"To complete your application, please verify your email address by clicking the link below.\n\n"
            f"Verification link:\n{verification_url}\n\n"
            f"This link will expire in 7 days.\n\n"
            f"Here's what we have on file:\n"
            f"  Practice type: {profile.get_practice_type_display()}\n"
            f"  Offerings: {profile.modalities}\n"
            f"  Location: {profile.location or 'Not specified'}\n\n"
            f"We'll review your application and reach out to this address ({profile.email}) when it's your turn.\n\n"
            f'— The {SITE_NAME} team'
        ),
        from_email=FROM_EMAIL,
        recipient_list=[profile.email],
        fail_silently=True,
    )


def send_status_change_notification(transition):
    """Send email notification when practitioner's status changes."""
    profile = transition.profile
    
    status_messages = {
        'reviewing': (
            'Your application is under review',
            f"Hi {profile.full_name},\n\n"
            f"We've received your application and our team is reviewing it. "
            f"We'll reach out within 3-5 business days with next steps.\n\n"
            f"Thanks for your patience!\n\n"
            f'— The {SITE_NAME} team'
        ),
        'invited': (
            'You\'re invited to join clairbook!',
            f"Hi {profile.full_name},\n\n"
            f"Great news! We'd love to have you on {SITE_NAME}. "
            f"Your application has been approved and you can now access your practitioner portal.\n\n"
            f"Next steps:\n"
            f"1. Log in at {SITE_URL}/accounts/login/\n"
            f"2. Complete your profile with services, pricing, and availability\n"
            f"3. Your profile will be live shortly\n\n"
            f"Questions? Reply to this email anytime.\n\n"
            f'— The {SITE_NAME} team'
        ),
        'onboarded': (
            'Welcome to clairbook!',
            f"Hi {profile.full_name},\n\n"
            f"Your profile is now live on {SITE_NAME}! "
            f"Practitioners and clients can now discover and connect with you.\n\n"
            f"Visit your practitioner dashboard:\n{SITE_URL}/professionals/dashboard/\n\n"
            f"Thanks for being part of our community.\n\n"
            f'— The {SITE_NAME} team'
        ),
    }
    
    if transition.to_status not in status_messages:
        return
    
    subject_line, message_body = status_messages[transition.to_status]
    
    send_mail(
        subject=f"[{SITE_NAME}] {subject_line}",
        message=message_body,
        from_email=FROM_EMAIL,
        recipient_list=[profile.email],
        fail_silently=True,
    )
