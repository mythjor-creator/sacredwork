import secrets
from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

User = get_user_model()


class EmailVerificationToken(models.Model):
    """Token for verifying email addresses during waitlist signup."""
    
    waitlist_profile = models.OneToOneField(
        'waitlist.PractitionerWaitlistProfile',
        on_delete=models.CASCADE,
        related_name='verification_token'
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def is_valid(self):
        """Check if token is still valid (not verified and not expired)."""
        if self.verified_at:
            return False
        age = timezone.now() - self.created_at
        return age < timedelta(days=7)  # 7-day expiry
    
    def verify(self):
        """Mark token as verified."""
        self.verified_at = timezone.now()
        self.save()
    
    @classmethod
    def create_for_profile(cls, profile):
        """Create a new verification token for a profile."""
        token = secrets.token_urlsafe(48)
        return cls.objects.create(
            waitlist_profile=profile,
            token=token
        )
    
    def __str__(self):
        return f'Token for {self.waitlist_profile.full_name}'


class GDPRDataExportLog(models.Model):
    """Log of GDPR data export requests for audit purposes."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='gdpr_exports')
    requested_at = models.DateTimeField(auto_now_add=True)
    exported_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f'Export request from {self.user} on {self.requested_at.strftime("%Y-%m-%d %H:%M")}'


class GDPRAccountDeletionLog(models.Model):
    """Log of GDPR account deletion requests for audit purposes."""
    
    user_identifier = models.CharField(max_length=255)  # Username/email preserved for audit
    requested_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_confirmed = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-requested_at']
    
    def __str__(self):
        return f'Deletion request for {self.user_identifier} on {self.requested_at.strftime("%Y-%m-%d %H:%M")}'
