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
from .forms import ReportProblemForm
from .models import EmailVerificationToken, GDPRDataExportLog, GDPRAccountDeletionLog


def privacy_view(request):
    """Render privacy policy page."""
    site_base_url = request.build_absolute_uri('/').rstrip('/')
    current_absolute_url = request.build_absolute_uri()
    return render(
        request,
        'pages/privacy.html',
        {
            'site_base_url': site_base_url,
            'current_absolute_url': current_absolute_url,
        },
    )


def healthcheck_view(request):
    """Lightweight uptime endpoint for load balancers and hosting healthchecks."""
    return JsonResponse({'status': 'ok'})


def style_sheet_view(request):
    """Render visual style sheet preview page."""
    profile = getattr(request.user, 'professional_profile', None) if request.user.is_authenticated else None
    return render(request, 'pages/style_sheet.html', {'profile': profile})


def about_view(request):
    """Render public about page with inclusive brand positioning."""
    site_base_url = request.build_absolute_uri('/').rstrip('/')
    current_absolute_url = request.build_absolute_uri()
    return render(
        request,
        'pages/about.html',
        {
            'site_base_url': site_base_url,
            'current_absolute_url': current_absolute_url,
        },
    )


def pricing_view(request):
    """Render public pricing page for practitioner tiers."""
    site_base_url = request.build_absolute_uri('/').rstrip('/')
    current_absolute_url = request.build_absolute_uri()
    pricing_tiers = [
        {
            'eyebrow': 'Basic practitioner',
            'title': 'A clear home for your profile and bookings.',
            'price': '60-day free trial',
            'subhead': 'Then standard practitioner pricing before any billing begins.',
            'features': [
                'Public practitioner profile',
                'Service listings with pricing and session format details',
                'Availability and booking management',
                'Access to account tools and profile editing',
            ],
            'cta_label': 'Start with practitioner access',
            'cta_href': '/waitlist/',
            'is_featured': False,
        },
        {
            'eyebrow': 'Featured',
            'title': 'For practitioners who want more visibility from day one.',
            'price': '60-day free trial',
            'subhead': 'Then featured placement pricing before any billing begins.',
            'features': [
                'Everything in Basic Practitioner',
                'Priority placement in featured rotations',
                'Additional discovery visibility across launch surfaces',
                'More prominent positioning for clients browsing your category',
            ],
            'cta_label': 'Join for featured consideration',
            'cta_href': '/waitlist/',
            'is_featured': True,
        },
        {
            'eyebrow': 'Founding',
            'title': 'A locked early rate for the first launch cohort.',
            'price': '$79/year',
            'subhead': 'Limited founding rate with priority onboarding and a founding badge.',
            'features': [
                'Founding member badge on your profile',
                'Rate locked at $79/year while your founding status remains active',
                'Priority onboarding into the launch cohort',
                'Reserved access for the first 100 founding practitioners',
            ],
            'cta_label': 'Claim founding access',
            'cta_href': '/waitlist/?founding=1#waitlist-profile',
            'is_featured': False,
        },
    ]
    return render(
        request,
        'pages/pricing.html',
        {
            'site_base_url': site_base_url,
            'current_absolute_url': current_absolute_url,
            'pricing_tiers': pricing_tiers,
        },
    )


def terms_view(request):
    """Render Help page with terms accordion and issue reporting form."""
    profile = getattr(request.user, 'professional_profile', None) if request.user.is_authenticated else None
    site_base_url = request.build_absolute_uri('/').rstrip('/')

    if request.method == 'POST':
        report_form = ReportProblemForm(request.POST)
        if report_form.is_valid():
            messages.success(request, 'Thanks for reporting this. We will review it shortly.')
            return redirect('pages:terms')
    else:
        report_form = ReportProblemForm(
            initial={'email': request.user.email if request.user.is_authenticated else ''}
        )

    return render(
        request,
        'pages/terms.html',
        {
            'profile': profile,
            'report_form': report_form,
            'site_base_url': site_base_url,
        },
    )


def verify_email_view(request, token):
    """Verify email using token from link in confirmation email."""
    verification = get_object_or_404(EmailVerificationToken, token=token)
    
    if not verification.is_valid():
        context = {
            'error': 'This verification link has expired. Please sign up again.' if verification.verified_at else 'This verification link has expired (7-day window).',
            'profile': verification.waitlist_profile,
            'current_absolute_url': request.build_absolute_uri(),
        }
        return render(request, 'pages/verify_email.html', context, status=400)
    
    # Mark as verified
    verification.verify()
    
    context = {
        'success': True,
        'profile': verification.waitlist_profile,
        'current_absolute_url': request.build_absolute_uri(),
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
