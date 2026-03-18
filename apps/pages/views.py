import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse, FileResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from django.db.models import Prefetch
from django.core.serializers.json import DjangoJSONEncoder

from apps.waitlist.models import PractitionerWaitlistProfile, StatusTransition
from apps.accounts.models import User
from .models import EmailVerificationToken, GDPRDataExportLog, GDPRAccountDeletionLog


def privacy_view(request):
    """Render privacy policy page."""
    return render(request, 'pages/privacy.html')


def terms_view(request):
    """Render terms of service page."""
    return render(request, 'pages/terms.html')


def verify_email_view(request, token):
    """Verify email using token from link in confirmation email."""
    verification = get_object_or_404(EmailVerificationToken, token=token)
    
    if not verification.is_valid():
        context = {
            'error': 'This verification link has expired. Please sign up again.' if verification.verified_at else 'This verification link has expired (7-day window).',
            'profile': verification.waitlist_profile,
        }
        return render(request, 'pages/verify_email.html', context, status=400)
    
    # Mark as verified
    verification.verify()
    
    context = {
        'success': True,
        'profile': verification.waitlist_profile,
    }
    return render(request, 'pages/verify_email.html', context)


@login_required
def gdpr_export_view(request):
    """Allow users to request/download their data as JSON."""
    if request.method == 'POST':
        # Create export log
        log = GDPRDataExportLog.objects.create(user=request.user)
        
        # Compile user data
        data = {
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'display_name': request.user.display_name,
                'role': request.user.get_role_display(),
                'created_at': request.user.date_joined.isoformat(),
            },
            'exported_at': timezone.now().isoformat(),
        }
        
        # Waitlist profile if applicable
        if hasattr(request.user, 'waitlist_profiles'):
            waitlist = request.user.waitlist_profiles.first()
            if waitlist:
                data['waitlist_profile'] = {
                    'id': waitlist.id,
                    'full_name': waitlist.full_name,
                    'email': waitlist.email,
                    'business_name': waitlist.business_name,
                    'headline': waitlist.headline,
                    'modalities': waitlist.modalities,
                    'practice_type': waitlist.get_practice_type_display(),
                    'location': waitlist.location,
                    'is_virtual': waitlist.is_virtual,
                    'offers_in_person': waitlist.offers_in_person,
                    'years_experience': waitlist.years_experience,
                    'status': waitlist.get_status_display(),
                    'status_changed_at': waitlist.status_changed_at.isoformat(),
                    'created_at': waitlist.created_at.isoformat(),
                }
        
        # Professional profile if applicable
        if hasattr(request.user, 'professional_profile'):
            prof = request.user.professional_profile
            if prof:
                services = [
                    {
                        'id': s.id,
                        'name': s.name,
                        'description': s.description,
                        'category': s.category.name,
                        'price_cents': s.price_cents,
                        'duration_minutes': s.duration_minutes,
                        'is_active': s.is_active,
                    }
                    for s in prof.services.all()
                ]
                data['professional_profile'] = {
                    'id': prof.id,
                    'bio': prof.bio,
                    'profile_photo_url': prof.profile_photo.url if prof.profile_photo else None,
                    'website_url': prof.website_url,
                    'is_verified': prof.is_verified,
                    'is_visible': prof.is_visible,
                    'approval_status': prof.get_approval_status_display(),
                    'services': services,
                    'created_at': prof.created_at.isoformat(),
                }
        
        # Generate downloadable JSON file
        response = HttpResponse(
            json.dumps(data, indent=2, cls=DjangoJSONEncoder),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="clairbook-data-{timezone.now().strftime("%Y%m%d")}.json"'
        
        # Update log
        log.exported_at = timezone.now()
        log.save()
        
        return response
    
    context = {}
    return render(request, 'pages/gdpr_export.html', context)


@login_required
def gdpr_delete_view(request):
    """Allow users to request account deletion."""
    if request.method == 'GET':
        return render(request, 'pages/gdpr_delete_confirm.html')
    
    if request.method == 'POST':
        confirm = request.POST.get('confirm_delete') == 'on'
        if not confirm:
            messages.error(request, 'You must confirm account deletion to proceed.')
            return render(request, 'pages/gdpr_delete_confirm.html')
        
        # Create deletion log before deleting user
        deletion_log = GDPRAccountDeletionLog.objects.create(
            user_identifier=f'{request.user.username} ({request.user.email})',
            deletion_confirmed=True,
        )
        
        # Store user info for audit
        user_id = request.user.id
        username = request.user.username
        
        # Delete user (cascade will delete related records)
        request.user.delete()
        
        # Mark deletion as complete
        deletion_log.deleted_at = timezone.now()
        deletion_log.save()
        
        messages.success(request, 'Your account and all associated data have been deleted.')
        return redirect('/')
    
    return render(request, 'pages/gdpr_delete_confirm.html')


def admin_gdpr_audit_view(request):
    """Admin view for GDPR audit logs (export/deletion requests)."""
    if not (request.user.is_staff and request.user.is_superuser):
        return redirect('admin:index')
    
    exports = GDPRDataExportLog.objects.all().select_related('user').order_by('-requested_at')
    deletions = GDPRAccountDeletionLog.objects.all().order_by('-requested_at')
    
    context = {
        'exports': exports,
        'deletions': deletions,
    }
    return render(request, 'pages/admin_gdpr_audit.html', context)
