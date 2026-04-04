import json
import logging
from urllib import error as urllib_error
from urllib import request as urllib_request

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.mail import send_mail
from django.urls import reverse

SITE_NAME = 'clairbook'
FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@sacredwork.app')
SITE_URL = getattr(settings, 'SITE_URL', 'http://localhost:8000')


logger = logging.getLogger(__name__)


def _waitlist_confirmation_code(lead):
    return f"SW-{lead.id:06d}"


def _waitlist_reply_to_email():
    return getattr(settings, 'WAITLIST_REPLY_TO_EMAIL', FROM_EMAIL)


def _resend_api_key():
    explicit_key = getattr(settings, 'RESEND_API_KEY', '')
    if explicit_key:
        return explicit_key
    email_host = getattr(settings, 'EMAIL_HOST', '')
    email_password = getattr(settings, 'EMAIL_HOST_PASSWORD', '')
    if email_host == 'smtp.resend.com' and email_password.startswith('re_'):
        return email_password
    return ''


def _send_via_resend_api(subject, message, to_email, reply_to=None):
    if not getattr(settings, 'RESEND_API_ENABLED', False):
        return False

    api_key = _resend_api_key()
    if not api_key:
        return False

    payload = {
        'from': FROM_EMAIL,
        'to': [to_email],
        'subject': subject,
        'text': message,
    }
    if reply_to:
        payload['reply_to'] = [reply_to]

    request = urllib_request.Request(
        getattr(settings, 'RESEND_API_URL', 'https://api.resend.com/emails'),
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    timeout = getattr(settings, 'EMAIL_TIMEOUT', 10)
    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode('utf-8', errors='replace')
        logger.info('Resend API accepted waitlist email for %s: %s', to_email, response_body)
        return True
    except urllib_error.HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='replace')
        raise RuntimeError(f'Resend API HTTP {exc.code}: {error_body}') from exc
    except urllib_error.URLError as exc:
        raise RuntimeError(f'Resend API connection failed: {exc.reason}') from exc


def send_waitlist_lead_confirmation(lead, generated_invite_code=None):
    """Send signup confirmation to a WaitlistLead.

    Every signup receives a confirmation code. Referred signups also receive
    their newly generated invite code in the same email.
    """
    first_name = (lead.name or '').split()[0] if lead.name else 'there'
    confirmation_code = _waitlist_confirmation_code(lead)
    used_referral = lead.invite_code_id is not None

    if used_referral:
        subject = "You're confirmed. Your invite code is inside."
        invite_line = generated_invite_code or 'Pending'
        message = (
            f"Hi {first_name},\n\n"
            f"You're officially on the {SITE_NAME} waitlist.\n\n"
            f"Confirmation code: {confirmation_code}\n"
            f"Your invite code: {invite_line}\n\n"
            f"You can share your invite code with trusted peers.\n"
            f"We'll email you as we roll out onboarding.\n\n"
            f"— The {SITE_NAME} team\n\n"
            f"Questions? Reply to this email."
        )
    else:
        subject = "You're confirmed on the waitlist"
        message = (
            f"Hi {first_name},\n\n"
            f"You're officially on the {SITE_NAME} waitlist.\n\n"
            f"Confirmation code: {confirmation_code}\n\n"
            f"Thanks for sharing your info with us. We'll follow up with next steps\n"
            f"as soon as your cohort is ready.\n\n"
            f"— The {SITE_NAME} team\n\n"
            f"Questions? Reply to this email."
        )

    if _send_via_resend_api(
        subject=subject,
        message=message,
        to_email=lead.email,
        reply_to=_waitlist_reply_to_email(),
    ):
        return

    EmailMessage(
        subject=subject,
        body=message,
        from_email=FROM_EMAIL,
        to=[lead.email],
        reply_to=[_waitlist_reply_to_email()],
    ).send(fail_silently=False)


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
        fail_silently=False,
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
