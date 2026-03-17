from django.test import TestCase
from django.urls import reverse

from .models import User


class AccountsFlowTests(TestCase):
	def test_professional_signup_redirects_to_onboarding(self):
		response = self.client.post(
			reverse('accounts:signup'),
			{
				'username': 'healer1',
				'display_name': 'Healer One',
				'email': 'healer@example.com',
				'role': User.Role.PROFESSIONAL,
				'password1': 'StrongPass123!!',
				'password2': 'StrongPass123!!',
			},
		)

		self.assertRedirects(response, reverse('professionals:onboarding'))
		created_user = User.objects.get(username='healer1')
		self.assertEqual(created_user.role, User.Role.PROFESSIONAL)

	def test_client_signup_redirects_to_dashboard(self):
		response = self.client.post(
			reverse('accounts:signup'),
			{
				'username': 'client1',
				'display_name': 'Client One',
				'email': 'client@example.com',
				'role': User.Role.CLIENT,
				'password1': 'StrongPass123!!',
				'password2': 'StrongPass123!!',
			},
		)

		self.assertRedirects(response, reverse('accounts:dashboard'))
