from .forms import SimpleWaitlistForm
# --- Minimal public waitlist signup ---
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def simple_waitlist_signup(request):
    if request.method == 'POST':
        form = SimpleWaitlistForm(request.POST)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.status = PractitionerWaitlistProfile.Status.NEW
            profile.save()
            return render(request, 'waitlist/success.html', {'profile': profile})
    else:
        form = SimpleWaitlistForm()
    return render(request, 'waitlist/simple_signup.html', {'form': form})
import logging
import re
import secrets
import string
from threading import Thread

from django.conf import settings
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect, render

from .emails import send_waitlist_confirmation, send_waitlist_lead_confirmation
from .forms import PractitionerWaitlistForm
from .models import PractitionerWaitlistProfile


logger = logging.getLogger(__name__)


def _generate_invite_code(segment_length=3, separator="-"):
    alphabet = string.ascii_uppercase + string.digits
    left = "".join(secrets.choice(alphabet) for _ in range(segment_length))
    right = "".join(secrets.choice(alphabet) for _ in range(segment_length))
    return f"{left}{separator}{right}"


def _normalize_referral_code(raw_code):
    cleaned = re.sub(r"[^A-Za-z0-9]", "", raw_code or "").upper()
    if len(cleaned) != 6:
        return None
    normalized = f"{cleaned[:3]}-{cleaned[3:]}"
    if not re.fullmatch(r"[A-Z0-9]{3}-[A-Z0-9]{3}", normalized):
        return None
    return normalized


def _send_waitlist_confirmation_background(profile):
    try:
        send_waitlist_confirmation(profile)
    except Exception:
        logger.exception('Waitlist confirmation email failed for profile_id=%s', profile.id)


def _send_lead_confirmation_background(lead, generated_invite_code):
    try:
        send_waitlist_lead_confirmation(lead, generated_invite_code=generated_invite_code)
    except Exception:
        logger.exception('Waitlist lead confirmation email failed for lead_id=%s', lead.id)


def waitlist_landing_view(request):
    """Render and process the TailGrid waitlist signup form as a single-page public form."""
    from .models import WaitlistLead, InviteCode
    context = {"success": False, "error": None}
    if request.method == "POST":
        name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        specialization = request.POST.get("specialization", "").strip()
        has_referral = request.POST.get("has_referral") == "yes"
        referral_code = request.POST.get("referral_code", "").strip()
        about = request.POST.get("about", "").strip()

        # Validate required fields
        if not name or not email:
            context["error"] = "Name and email are required."
        elif has_referral and not referral_code:
            context["error"] = "Referral code is required."
        elif not has_referral and not about:
            context["error"] = "Please tell us about yourself."
        else:
            try:
                invite = None
                normalized_referral_code = None
                new_invite_code = None
                if has_referral:
                    normalized_referral_code = _normalize_referral_code(referral_code)
                    if not normalized_referral_code:
                        context["error"] = "Referral code must match XXX-XXX."
                    else:
                        invite = InviteCode.objects.filter(code=normalized_referral_code, is_active=True, uses_remaining__gt=0).first()
                    if normalized_referral_code and not invite:
                        context["error"] = "Invalid or inactive referral code."
                if not context["error"]:
                    lead = WaitlistLead.objects.create(
                        name=name,
                        email=email,
                        role=specialization,
                        invite_code=invite if invite else None,
                        notes=about if not has_referral else "",
                    )
                    if has_referral and invite:
                        invite.uses_remaining -= 1
                        if invite.uses_remaining <= 0:
                            invite.is_active = False
                        invite.save()
                        # Generate a new unique invite code for the new user
                        while True:
                            code = _generate_invite_code()
                            if not InviteCode.objects.filter(code__iexact=code).exists():
                                break
                        new_invite_code = InviteCode.objects.create(code=code, is_active=True, owner=lead)

                    # Send confirmation email in a background thread so slow
                    # SMTP does not block the form response in production.
                    Thread(
                        target=_send_lead_confirmation_background,
                        args=(lead, new_invite_code.code if new_invite_code else None),
                        daemon=True,
                    ).start()
                    context["success"] = True
            except Exception as e:
                context["error"] = str(e)
        if context["success"]:
            # Pass the new invite code (if any) to the confirmation template
            return render(request, "waitlist/success.html", {"name": name, "new_invite_code": new_invite_code.code if has_referral and new_invite_code else None})
    return render(request, 'waitlist/signup.html', context)
