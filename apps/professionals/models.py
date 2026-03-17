from django.db import models


class ProfessionalProfile(models.Model):
	class ApprovalStatus(models.TextChoices):
		DRAFT = 'draft', 'Draft'
		PENDING = 'pending', 'Pending Review'
		APPROVED = 'approved', 'Approved'
		REJECTED = 'rejected', 'Rejected'

	user = models.OneToOneField(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='professional_profile',
	)
	business_name = models.CharField(max_length=180)
	headline = models.CharField(max_length=220)
	bio = models.TextField()
	modalities = models.CharField(max_length=255, help_text='Comma-separated offerings')
	location = models.CharField(max_length=120, blank=True)
	is_virtual = models.BooleanField(default=True)
	years_experience = models.PositiveSmallIntegerField(default=0)
	profile_image_url = models.URLField(blank=True)
	approval_status = models.CharField(
		max_length=20,
		choices=ApprovalStatus.choices,
		default=ApprovalStatus.DRAFT,
	)
	is_visible = models.BooleanField(default=False)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['business_name']

	def __str__(self) -> str:
		return self.business_name
