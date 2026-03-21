from django.db import models


class SubscriptionPlan(models.Model):
    class BillingInterval(models.TextChoices):
        MONTH = 'month', 'Monthly'
        YEAR = 'year', 'Yearly'

    code = models.SlugField(max_length=50, unique=True)
    name = models.CharField(max_length=120)
    amount_cents = models.PositiveIntegerField()
    billing_interval = models.CharField(
        max_length=20,
        choices=BillingInterval.choices,
        default=BillingInterval.YEAR,
    )
    stripe_price_id = models.CharField(max_length=255, blank=True)
    founding_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'amount_cents', 'name']

    def __str__(self) -> str:
        return self.name

    @property
    def amount_display(self) -> str:
        return f'{self.amount_cents / 100:.2f}'


class ProfessionalSubscription(models.Model):
    class Status(models.TextChoices):
        PENDING_LAUNCH = 'pending_launch', 'Pending Launch'
        ACTIVE = 'active', 'Active'
        PAST_DUE = 'past_due', 'Past Due'
        CANCELED = 'canceled', 'Canceled'

    professional = models.OneToOneField(
        'professionals.ProfessionalProfile',
        on_delete=models.CASCADE,
        related_name='subscription',
    )
    plan = models.ForeignKey(
        SubscriptionPlan,
        on_delete=models.PROTECT,
        related_name='subscriptions',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_LAUNCH,
        db_index=True,
    )
    stripe_customer_id = models.CharField(max_length=255, blank=True, db_index=True)
    stripe_subscription_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    founding_member_rate_locked = models.BooleanField(default=False)
    cancel_at_period_end = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f'{self.professional.display_name} subscription'


class SubscriptionInvoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        OPEN = 'open', 'Open'
        PAID = 'paid', 'Paid'
        VOID = 'void', 'Void'
        UNCOLLECTIBLE = 'uncollectible', 'Uncollectible'

    subscription = models.ForeignKey(
        ProfessionalSubscription,
        on_delete=models.CASCADE,
        related_name='invoices',
    )
    stripe_invoice_id = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    amount_due_cents = models.PositiveIntegerField(default=0)
    amount_paid_cents = models.PositiveIntegerField(default=0)
    currency = models.CharField(max_length=10, default='usd')
    hosted_invoice_url = models.URLField(blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return self.stripe_invoice_id


class BillingWebhookEvent(models.Model):
    stripe_event_id = models.CharField(max_length=255, unique=True)
    event_type = models.CharField(max_length=120, blank=True)
    is_processing = models.BooleanField(default=False)
    attempt_count = models.PositiveIntegerField(default=0)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-received_at']

    def __str__(self) -> str:
        return self.stripe_event_id
