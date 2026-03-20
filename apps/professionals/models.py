from django.db import models


class ProfessionalProfile(models.Model):
	class SubscriptionStatus(models.TextChoices):
		NOT_STARTED = 'not_started', 'Not Started'
		PRELAUNCH = 'prelaunch', 'Prelaunch Access'
		ACTIVE = 'active', 'Active'
		PAST_DUE = 'past_due', 'Past Due'
		CANCELED = 'canceled', 'Canceled'
		GRANDFATHERED = 'grandfathered', 'Grandfathered'

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
	profile_photo = models.ImageField(upload_to='professionals/profile_photos/', blank=True)
	long_bio = models.TextField(blank=True)
	approval_status = models.CharField(
		max_length=20,
		choices=ApprovalStatus.choices,
		default=ApprovalStatus.DRAFT,
	)
	subscription_status = models.CharField(
		max_length=20,
		choices=SubscriptionStatus.choices,
		default=SubscriptionStatus.NOT_STARTED,
		db_index=True,
	)
	stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
	subscription_fails_count = models.PositiveSmallIntegerField(default=0)
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
		has_gallery = self.gallery_images.filter(is_active=True).exists()
		has_credentials = self.credentials.filter(is_active=True).exists()
		return [
			('Profile photo', bool(self.profile_photo or self.profile_image_url)),
			('Bio (50+ characters)', len(self.bio.strip()) >= 50),
			('Expanded bio', len(self.long_bio.strip()) >= 120),
			('Location', bool(self.location.strip())),
			('Modalities', bool(self.modalities.strip())),
			('At least one active service', has_service),
			('Gallery photo (in-person services)', has_gallery),
			('Credential added (optional)', has_credentials),
		]

	@property
	def completeness_percent(self) -> int:
		checks = self.completeness_checks
		done = sum(1 for _, ok in checks if ok)
		return round(done / len(checks) * 100)

	@property
	def billing_access_granted(self) -> bool:
		return self.subscription_status in {
			self.SubscriptionStatus.PRELAUNCH,
			self.SubscriptionStatus.ACTIVE,
			self.SubscriptionStatus.GRANDFATHERED,
		}

	def __str__(self) -> str:
		return self.display_name


class ProfileGalleryImage(models.Model):
	profile = models.ForeignKey(
		ProfessionalProfile,
		on_delete=models.CASCADE,
		related_name='gallery_images',
	)
	image = models.ImageField(upload_to='professionals/gallery/')
	caption = models.CharField(max_length=180, blank=True)
	is_active = models.BooleanField(default=True)
	sort_order = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['sort_order', 'id']

	def __str__(self) -> str:
		return f'Gallery image for {self.profile.display_name}'


class ProfessionalCredential(models.Model):
	class CredentialType(models.TextChoices):
		CERTIFICATION = 'certification', 'Certification'
		EDUCATION = 'education', 'Education'
		LICENSE = 'license', 'License'
		OTHER = 'other', 'Other'

	profile = models.ForeignKey(
		ProfessionalProfile,
		on_delete=models.CASCADE,
		related_name='credentials',
	)
	credential_type = models.CharField(
		max_length=20,
		choices=CredentialType.choices,
		default=CredentialType.CERTIFICATION,
	)
	title = models.CharField(max_length=180)
	organization = models.CharField(max_length=180, blank=True)
	license_number = models.CharField(max_length=120, blank=True)
	issued_on = models.DateField(null=True, blank=True)
	expires_on = models.DateField(null=True, blank=True)
	verification_url = models.URLField(blank=True)
	notes = models.CharField(max_length=255, blank=True)
	is_active = models.BooleanField(default=True)
	sort_order = models.PositiveSmallIntegerField(default=0)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['sort_order', 'title']

	def __str__(self) -> str:
		return f'{self.get_credential_type_display()}: {self.title}'
