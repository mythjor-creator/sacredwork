from django.db import models


class Category(models.Model):
	name = models.CharField(max_length=80, unique=True)
	slug = models.SlugField(max_length=100, unique=True)
	description = models.TextField(blank=True)

	class Meta:
		ordering = ['name']
		verbose_name_plural = 'categories'

	def __str__(self) -> str:
		return self.name


class Service(models.Model):
	class DeliveryFormat(models.TextChoices):
		IN_PERSON = 'in_person', 'In Person'
		VIRTUAL = 'virtual', 'Virtual'
		BOTH = 'both', 'Both'

	professional = models.ForeignKey(
		'professionals.ProfessionalProfile',
		on_delete=models.CASCADE,
		related_name='services',
	)
	category = models.ForeignKey(
		Category,
		on_delete=models.PROTECT,
		related_name='services',
	)
	name = models.CharField(max_length=140)
	description = models.TextField()
	duration_minutes = models.PositiveSmallIntegerField()
	price_cents = models.PositiveIntegerField()
	delivery_format = models.CharField(
		max_length=20,
		choices=DeliveryFormat.choices,
		default=DeliveryFormat.VIRTUAL,
	)
	is_active = models.BooleanField(default=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['name']

	def __str__(self) -> str:
		return f'{self.name} - {self.professional.business_name}'

	@property
	def price_display(self) -> str:
		return f'{self.price_cents / 100:.2f}'

	@property
	def duration_display(self) -> str:
		minutes = self.duration_minutes
		if minutes < 60:
			return f'{minutes} min'
		hours, rem = divmod(minutes, 60)
		if rem == 0:
			return f'{hours} hr' if hours == 1 else f'{hours} hrs'
		return f'{hours} hr {rem} min'


class AnalyticsEvent(models.Model):
	"""Simple first-party analytics event store for funnel reporting."""

	name = models.CharField(max_length=80, db_index=True)
	source = models.CharField(max_length=40, blank=True)
	has_query = models.BooleanField(default=False)
	has_category = models.BooleanField(default=False)
	profile_id = models.PositiveIntegerField(null=True, blank=True)
	path = models.CharField(max_length=255, blank=True)
	user = models.ForeignKey(
		'accounts.User',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='analytics_events',
	)
	created_at = models.DateTimeField(auto_now_add=True, db_index=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'{self.name} ({self.source or "unknown"})'
