from django.conf import settings
from django.core.mail import send_mail
from django.urls import reverse

SITE_NAME = 'clairbook'
FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sacredwork.app')
SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000')


def send_waitlist_confirmation(profile):
    """Send confirmation email after a practitioner joins the waitlist.

    Sends founding-member copy if profile.is_founding_member is True,
    otherwise sends the standard free-waitlist confirmation.
    """
    from apps.pages.models import EmailVerificationToken

    token = EmailVerificationToken.create_for_profile(profile)
    verification_url = f"{SITE_URL}{reverse('pages:verify_email', args=[token.token])}"
    first_name = profile.full_name.split()[0] if profile.full_name else profile.full_name

    if profile.is_founding_member:
        subject = "You're in."
        message = (
            f"Hi {first_name},\n\n"
            f"You're one of our founding practitioners. That actually means something to us.\n\n"
            f"Your spot is reserved, your rate is locked, and your profile launches when we do. Until then, "
            f"you'll hear from us directly\u2014just real updates about the build and the occasional question "
            f"where your input actually shapes what we make.\n\n"
            f"A few things to know:\n"
            f"  \u00b7 Your $79/year rate is locked in permanently, no matter how long you're with us.\n"
            f"  \u00b7 You'll get early access to set up your profile before we open publicly.\n"
            f"  \u00b7 If we don't launch, you get a full refund. No process, no questions.\n\n"
            f"One last step \u2014 please verify your email so we can keep your spot secure:\n"
            f"{verification_url}\n\n"
            f"This link expires in 7 days.\n\n"
            f"We're building this with you in mind. Thank you for being here early.\n\n"
            f"\u2014 The {SITE_NAME} team\n\n"
            f"Questions? Reply to this email."
        )
    else:
        subject = "You're on the list."
        message = (
            f"Hi {first_name},\n\n"
            f"You're on the {SITE_NAME} waitlist. We'll reach out before we launch so you're first to know.\n\n"
            f"If you know another practitioner who'd fit well here, send them our way. "
            f"The community we're building is only as strong as the people in it.\n\n"
            f"Please verify your email to confirm your spot:\n"
            f"{verification_url}\n\n"
            f"This link expires in 7 days.\n\n"
            f"\u2014 The {SITE_NAME} team"
        )

    send_mail(
        subject=subject,
        message=message,
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
