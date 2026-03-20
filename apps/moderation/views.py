from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.professionals.models import ProfessionalProfile
from apps.catalog.models import Service
from .models import ModerationDecision


def _is_staff(user):
	"""Check if user is staff."""
	return user.is_staff


@login_required
@user_passes_test(_is_staff)
def moderation_queue_view(request):
	"""Display staff moderation queue of pending professional profiles."""
	# Get profiles pending review
	pending_profiles = ProfessionalProfile.objects.filter(
		approval_status=ProfessionalProfile.ApprovalStatus.PENDING,
	).select_related('user').prefetch_related('services').order_by('created_at')
	
	# Get profiles already reviewed
	reviewed_profiles = ProfessionalProfile.objects.exclude(
		approval_status=ProfessionalProfile.ApprovalStatus.PENDING,
	).select_related('user').order_by('-updated_at')[:20]
	
	return render(
		request,
		'moderation/queue.html',
		{
			'pending_profiles': pending_profiles,
			'reviewed_profiles': reviewed_profiles,
			'queue_count': pending_profiles.count(),
		},
	)


@login_required
@user_passes_test(_is_staff)
@require_POST
def moderation_decide_view(request, profile_id):
	"""Handle moderation decision (approve/reject)."""
	profile = get_object_or_404(ProfessionalProfile, pk=profile_id)
	decision = request.POST.get('decision', '').lower().strip()
	notes = request.POST.get('notes', '').strip()
	
	if decision not in ['approved', 'rejected']:
		messages.error(request, 'Invalid decision.')
		return redirect('moderation:queue')
	
	# Create decision record
	ModerationDecision.objects.create(
		profile=profile,
		decided_by=request.user,
		decision=decision,
		notes=notes,
	)
	
	# Update profile status
	if decision == 'approved':
		profile.approval_status = ProfessionalProfile.ApprovalStatus.APPROVED
		profile.is_visible = True
		messages.success(request, f'{profile.display_name} approved and is now visible.')
	else:
		profile.approval_status = ProfessionalProfile.ApprovalStatus.REJECTED
		profile.is_visible = False
		messages.warning(request, f'{profile.display_name} rejected and is now hidden.')
	
	profile.save(update_fields=['approval_status', 'is_visible', 'updated_at'])
	return redirect('moderation:queue')
