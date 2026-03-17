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
