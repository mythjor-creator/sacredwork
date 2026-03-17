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
	def __str__(self) -> str:
		return self.display_name
