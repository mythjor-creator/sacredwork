from django.conf import settings
from django.db import models
# Minimal InviteCode and WaitlistLead models for invite-only waitlist

class InviteCode(models.Model):
    code = models.CharField(max_length=32, unique=True)
    is_active = models.BooleanField(default=True)
    uses_remaining = models.PositiveIntegerField(default=1000)
    owner = models.ForeignKey(
        'WaitlistLead',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='owned_invite_codes',
    )
    admin_owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='admin_owned_invite_codes',
        help_text='Admin user responsible for this invite code.',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.code


class WaitlistLead(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=64, blank=True)
    invite_code = models.ForeignKey(InviteCode, null=True, blank=True, on_delete=models.PROTECT)
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.email})"
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()


class PractitionerWaitlistProfile(models.Model):
    class SignupTier(models.TextChoices):
        FREE = 'free', 'Free Waitlist'
        BASIC = 'basic', 'Basic Practitioner'
        FEATURED = 'featured', 'Featured'
        FOUNDING = 'founding', 'Founding'

    class PracticeType(models.TextChoices):
        WELLNESS = 'wellness', 'Wellness'
        SPIRITUAL = 'spiritual', 'Spiritual'
        BEAUTY = 'beauty', 'Beauty'
        COACHING = 'coaching', 'Coaching'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        NEW = 'new', 'New'
        REVIEWING = 'reviewing', 'Reviewing'
        INVITED = 'invited', 'Invited'
        ONBOARDED = 'onboarded', 'Onboarded'

    full_name = models.CharField(max_length=120)
    email = models.EmailField(unique=True)
    business_name = models.CharField(max_length=180, blank=True, default='')
    headline = models.CharField(max_length=220)
    modalities = models.CharField(max_length=255, help_text='Comma-separated offerings')
    practice_type = models.CharField(max_length=20, choices=PracticeType.choices)
    location = models.CharField(max_length=120, blank=True)
    is_virtual = models.BooleanField(default=True)
    offers_in_person = models.BooleanField(default=False)
    years_experience = models.PositiveSmallIntegerField(default=0)
    website_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    is_founding_member = models.BooleanField(
        default=False,
        help_text='Opted in for the founding practitioner rate at sign-up.',
    )
    signup_tier = models.CharField(
        max_length=20,
        choices=SignupTier.choices,
        default=SignupTier.FREE,
        db_index=True,
        help_text='Selected signup flow from pricing and waitlist entry points.',
    )
    is_test_data = models.BooleanField(
        default=False,
        db_index=True,
        help_text='Marks internal, demo, seeded, or QA signups so they can be separated from real submissions.',
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    status_changed_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        previous_status = None
        if self.pk:
            previous_status = type(self).objects.filter(pk=self.pk).values_list('status', flat=True).first()

        if previous_status is not None and previous_status != self.status:
            self.status_changed_at = timezone.now()
            update_fields = kwargs.get('update_fields')
            if update_fields is not None:
                merged_fields = set(update_fields)
                merged_fields.add('status_changed_at')
                kwargs['update_fields'] = list(merged_fields)
            
            # Create transition record (will be assigned current user by admin action if needed)
            StatusTransition.objects.create(
                profile=self,
                from_status=previous_status,
                to_status=self.status,
                changed_at=self.status_changed_at,
            )

        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f'{self.full_name} ({self.email})'


class StatusTransition(models.Model):
    """Track all status changes for a practitioner waitlist profile."""
    
    profile = models.ForeignKey(
        PractitionerWaitlistProfile,
        on_delete=models.CASCADE,
        related_name='status_transitions'
    )
    from_status = models.CharField(
        max_length=20,
        choices=PractitionerWaitlistProfile.Status.choices,
    )
    to_status = models.CharField(
        max_length=20,
        choices=PractitionerWaitlistProfile.Status.choices,
    )
    changed_at = models.DateTimeField(default=timezone.now, db_index=True)
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_transitions_changed'
    )
    reason = models.TextField(blank=True, help_text='Optional reason for status change')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['profile', '-changed_at']),
        ]

    def __str__(self) -> str:
        return f'{self.profile.full_name}: {self.from_status} → {self.to_status} at {self.changed_at.strftime("%Y-%m-%d %H:%M")}'
