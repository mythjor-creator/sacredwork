from django.test import TestCase
from django.urls import reverse

from apps.professionals.models import ProfessionalProfile

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

		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

	def test_dashboard_redirects_professional_without_profile_to_onboarding(self):
		user = User.objects.create_user(
			username='pro_no_profile',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.client.force_login(user)

		response = self.client.get(reverse('accounts:dashboard'))
		self.assertRedirects(response, reverse('professionals:onboarding'))

	def test_dashboard_redirects_professional_with_profile_to_profile_edit(self):
		user = User.objects.create_user(
			username='pro_with_profile',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		ProfessionalProfile.objects.create(
			user=user,
			headline='Test headline',
			bio='Test bio',
			modalities='reiki',
			years_experience=3,
		)
		self.client.force_login(user)

		response = self.client.get(reverse('accounts:dashboard'))
		self.assertRedirects(response, reverse('professionals:profile_core'))

	def test_dashboard_redirects_client_to_marketplace(self):
		user = User.objects.create_user(
			username='client_dashboard',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(user)

		response = self.client.get(reverse('accounts:dashboard'))
		self.assertRedirects(response, reverse('catalog:marketplace'))

	def test_account_settings_page_requires_login(self):
		response = self.client.get(reverse('accounts:settings'))
		self.assertEqual(response.status_code, 302)

	def test_account_settings_updates_profile_fields(self):
		user = User.objects.create_user(
			username='settings_user',
			password='StrongPass123!!',
			email='before@example.com',
			display_name='Before Name',
			role=User.Role.CLIENT,
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('accounts:settings'),
			{
				'action': 'update_profile',
				'display_name': 'After Name',
				'first_name': 'After',
				'last_name': 'User',
				'username': 'settings_user',
				'email': 'after@example.com',
			},
		)

		self.assertRedirects(response, reverse('accounts:settings'))
		user.refresh_from_db()
		self.assertEqual(user.display_name, 'After Name')
		self.assertEqual(user.first_name, 'After')
		self.assertEqual(user.last_name, 'User')
		self.assertEqual(user.email, 'after@example.com')

	def test_account_settings_changes_password(self):
		user = User.objects.create_user(
			username='password_user',
			password='OldPass123!!',
			display_name='Password User',
			email='password@example.com',
			role=User.Role.CLIENT,
		)
		self.client.force_login(user)

		response = self.client.post(
			reverse('accounts:settings'),
			{
				'action': 'change_password',
				'old_password': 'OldPass123!!',
				'new_password1': 'NewPass123!!',
				'new_password2': 'NewPass123!!',
			},
		)

		self.assertRedirects(response, reverse('accounts:settings'))
		user.refresh_from_db()
		self.assertTrue(user.check_password('NewPass123!!'))
		settings_response = self.client.get(reverse('accounts:settings'))
		self.assertEqual(settings_response.status_code, 200)

	def test_account_settings_uses_portal_wrapper_for_professional(self):
		user = User.objects.create_user(
			username='portal_settings_user',
			password='StrongPass123!!',
			display_name='Portal Settings',
			email='portal-settings@example.com',
			role=User.Role.PROFESSIONAL,
		)
		ProfessionalProfile.objects.create(
			user=user,
			headline='Profile headline',
			bio='Profile bio',
			modalities='reiki',
		)
		self.client.force_login(user)

		response = self.client.get(reverse('accounts:settings'))
		self.assertContains(response, 'practitioner-account-portal')
		self.assertContains(response, 'Danger zone')
		self.assertContains(response, 'Export my data')

	def test_authenticated_top_nav_includes_pricing_link(self):
		user = User.objects.create_user(
			username='nav_user',
			password='StrongPass123!!',
			email='nav-user@clairbook.com',
			role=User.Role.CLIENT,
		)
		self.client.force_login(user)

		response = self.client.get(reverse('accounts:settings'))
		self.assertContains(response, reverse('pages:pricing'))
