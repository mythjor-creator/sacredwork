from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
	class Role(models.TextChoices):
		CLIENT = 'client', 'Client'
		PROFESSIONAL = 'professional', 'Professional'
		ADMIN = 'admin', 'Admin'

	role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
	display_name = models.CharField(max_length=120, blank=True)
	is_test_account = models.BooleanField(
		default=False,
		db_index=True,
		help_text='Marks internal, demo, seeded, or QA accounts so they can be separated from real users.',
	)

	def __str__(self) -> str:
		return self.display_name or self.username
