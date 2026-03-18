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
	business_name = models.CharField(max_length=180, blank=True, default='')
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
	is_verified = models.BooleanField(
		default=False,
		db_index=True,
		help_text='Staff-verified badge shown publicly on the profile page.',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['user__display_name', 'business_name']

	@property
	def practitioner_name(self) -> str:
		if self.user.display_name:
			return self.user.display_name
		if self.business_name:
			return self.business_name
		return self.user.username

	@property
	def display_name(self) -> str:
		return self.practitioner_name

	@property
	def business_name_suffix(self) -> str:
		if self.business_name and self.business_name != self.display_name:
			return f' · {self.business_name}'
		return ''

	@property
	def completeness_checks(self) -> list:
		"""Return a list of (label, is_complete) tuples for profile completeness UI."""
		has_service = self.services.filter(is_active=True).exists()
		return [
			('Profile photo', bool(self.profile_image_url)),
			('Bio (50+ characters)', len(self.bio.strip()) >= 50),
			('Location', bool(self.location.strip())),
			('Modalities', bool(self.modalities.strip())),
			('At least one active service', has_service),
		]

	@property
	def completeness_percent(self) -> int:
		checks = self.completeness_checks
		done = sum(1 for _, ok in checks if ok)
		return round(done / len(checks) * 100)

	def __str__(self) -> str:
		return self.display_name
