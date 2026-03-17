from django.db import models


class ModerationDecision(models.Model):
	class Decision(models.TextChoices):
		APPROVED = 'approved', 'Approved'
		REJECTED = 'rejected', 'Rejected'

	profile = models.ForeignKey(
		'professionals.ProfessionalProfile',
		on_delete=models.CASCADE,
		related_name='moderation_decisions',
		null=True,
		blank=True,
	)
	service = models.ForeignKey(
		'catalog.Service',
		on_delete=models.CASCADE,
		related_name='moderation_decisions',
		null=True,
		blank=True,
	)
	decided_by = models.ForeignKey(
		'accounts.User',
		on_delete=models.PROTECT,
		related_name='moderation_decisions',
	)
	decision = models.CharField(max_length=20, choices=Decision.choices)
	notes = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self) -> str:
		target = self.profile or self.service
		return f'{self.decision} - {target}'
