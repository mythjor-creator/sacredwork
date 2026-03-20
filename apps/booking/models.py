from django.db import models


class AvailabilityWindow(models.Model):
	class Weekday(models.IntegerChoices):
		MONDAY = 1, 'Monday'
		TUESDAY = 2, 'Tuesday'
		WEDNESDAY = 3, 'Wednesday'
		THURSDAY = 4, 'Thursday'
		FRIDAY = 5, 'Friday'
		SATURDAY = 6, 'Saturday'
		SUNDAY = 7, 'Sunday'

	professional = models.ForeignKey(
		'professionals.ProfessionalProfile',
		on_delete=models.CASCADE,
		related_name='availability_windows',
	)
	weekday = models.PositiveSmallIntegerField(choices=Weekday.choices)
	start_time = models.TimeField()
	end_time = models.TimeField()
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['professional', 'weekday', 'start_time']

	def __str__(self) -> str:
		return f'{self.professional.display_name} {self.get_weekday_display()} {self.start_time}-{self.end_time}'

	@property
	def status_suffix(self) -> str:
		return ' · Inactive' if not self.is_active else ''


class Booking(models.Model):
	class Status(models.TextChoices):
		REQUESTED = 'requested', 'Requested'
		CONFIRMED = 'confirmed', 'Confirmed'
		CANCELLED = 'cancelled', 'Cancelled'
		COMPLETED = 'completed', 'Completed'

	client = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='client_bookings',
	)
	professional = models.ForeignKey(
		'professionals.ProfessionalProfile',
		on_delete=models.CASCADE,
		related_name='bookings',
	)
	service = models.ForeignKey(
		'catalog.Service',
		on_delete=models.PROTECT,
		related_name='bookings',
	)
	start_at = models.DateTimeField()
	end_at = models.DateTimeField()
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.REQUESTED)
	intake_notes = models.TextField(blank=True)
	price_cents_snapshot = models.PositiveIntegerField()
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-start_at']
		constraints = [
			models.UniqueConstraint(
				fields=['professional', 'start_at'],
				name='unique_professional_slot',
			)
		]

	def __str__(self) -> str:
		return f'{self.service.name} with {self.professional.display_name} at {self.start_at}'

	@property
	def price_display(self) -> str:
		return f'{self.price_cents_snapshot / 100:.2f}'

	@property
	def is_requested(self) -> bool:
		return self.status == self.Status.REQUESTED

	@property
	def is_confirmed(self) -> bool:
		return self.status == self.Status.CONFIRMED


class BookingPaymentIntent(models.Model):
	class Status(models.TextChoices):
		PENDING = 'pending', 'Pending'
		COMPLETED = 'completed', 'Completed'
		EXPIRED = 'expired', 'Expired'
		FAILED = 'failed', 'Failed'

	client = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='booking_payment_intents',
	)
	service = models.ForeignKey(
		'catalog.Service',
		on_delete=models.PROTECT,
		related_name='payment_intents',
	)
	start_at = models.DateTimeField()
	intake_notes = models.TextField(blank=True)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
	stripe_checkout_session_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
	stripe_payment_intent_id = models.CharField(max_length=255, blank=True)
	failure_reason = models.CharField(max_length=255, blank=True)
	requires_manual_refund = models.BooleanField(default=False)
	refund_id = models.CharField(max_length=255, blank=True, help_text='Stripe refund ID (re_...) once issued.')
	refund_resolved_at = models.DateTimeField(null=True, blank=True, help_text='When the manual refund was marked resolved.')
	booking = models.OneToOneField(
		Booking,
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='payment_intent',
	)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self) -> str:
		return f'Payment intent {self.pk} for {self.service.name}'


class BookingHold(models.Model):
	"""Short-lived reservation to prevent concurrent booking of the same slot."""

	client = models.ForeignKey(
		'accounts.User',
		on_delete=models.CASCADE,
		related_name='booking_holds',
	)
	professional = models.ForeignKey(
		'professionals.ProfessionalProfile',
		on_delete=models.CASCADE,
		related_name='booking_holds',
	)
	service = models.ForeignKey(
		'catalog.Service',
		on_delete=models.CASCADE,
		related_name='booking_holds',
	)
	start_at = models.DateTimeField()
	expires_at = models.DateTimeField()
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']
		# Prevent multiple holds for the same slot
		constraints = [
			models.UniqueConstraint(
				fields=['professional', 'start_at'],
				name='unique_professional_hold_slot',
			)
		]

	def __str__(self) -> str:
		return f'Hold {self.pk}: {self.service.name} with {self.professional.display_name} at {self.start_at}'

	@property
	def is_expired(self) -> bool:
		from django.utils import timezone
		return timezone.now() >= self.expires_at
