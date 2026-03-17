from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.core.management import call_command

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile

from .models import Category, Service


class MarketplaceDiscoveryTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Energy Work', slug='energy-work')
		professional_user = User.objects.create_user(
			username='visible-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.visible_profile = ProfessionalProfile.objects.create(
			user=professional_user,
			business_name='Visible Healing Studio',
			headline='Breathwork and reiki guide',
			bio='Supportive healing sessions for nervous system regulation.',
			modalities='reiki, breathwork',
			location='Los Angeles',
			is_virtual=True,
			years_experience=6,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		Service.objects.create(
			professional=self.visible_profile,
			category=self.category,
			name='Reiki Reset',
			description='A grounding virtual session.',
			duration_minutes=60,
			price_cents=12500,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

		hidden_user = User.objects.create_user(
			username='hidden-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		hidden_profile = ProfessionalProfile.objects.create(
			user=hidden_user,
			business_name='Hidden Practice',
			headline='Pending review',
			bio='Should not appear publicly.',
			modalities='coaching',
			location='New York',
			is_virtual=True,
			years_experience=2,
			approval_status=ProfessionalProfile.ApprovalStatus.PENDING,
			is_visible=False,
		)
		Service.objects.create(
			professional=hidden_profile,
			category=self.category,
			name='Invisible Service',
			description='Hidden until moderation approves.',
			duration_minutes=45,
			price_cents=9000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

	def test_marketplace_shows_only_visible_approved_profiles(self):
		response = self.client.get(reverse('catalog:marketplace'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Visible Healing Studio')
		self.assertNotContains(response, 'Hidden Practice')

	def test_marketplace_can_filter_by_search_and_category(self):
		response = self.client.get(
			reverse('catalog:marketplace'),
			{'q': 'reiki', 'category': self.category.slug},
		)

		self.assertContains(response, 'Visible Healing Studio')
		self.assertContains(response, 'Reiki Reset')

	def test_marketplace_preview_badge_shows_only_in_sample_mode(self):
		response_without_sample = self.client.get(reverse('catalog:marketplace'))
		self.assertNotContains(response_without_sample, 'Preview mode: sample data')

		with override_settings(DEBUG=True):
			response_with_sample = self.client.get(reverse('catalog:marketplace'), {'sample': '1'})
		self.assertContains(response_with_sample, 'Preview mode: sample data')


class ServiceManagementTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Coaching', slug='coaching')
		self.professional_user = User.objects.create_user(
			username='service-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Aligned Coaching',
			headline='Transformational coach',
			bio='Coaching for transitions.',
			modalities='coaching, leadership',
			location='Seattle',
			is_virtual=True,
			years_experience=8,
			approval_status=ProfessionalProfile.ApprovalStatus.PENDING,
			is_visible=False,
		)

	def test_professional_can_create_service(self):
		self.client.force_login(self.professional_user)

		response = self.client.post(
			reverse('catalog:service_create'),
			{
				'category': self.category.pk,
				'name': 'Clarity Session',
				'description': 'A focused coaching session.',
				'duration_minutes': 75,
				'price_cents': 15000,
				'delivery_format': Service.DeliveryFormat.VIRTUAL,
				'is_active': True,
			},
		)

		self.assertRedirects(response, reverse('catalog:service_list'))
		self.assertTrue(self.profile.services.filter(name='Clarity Session').exists())

	def test_client_cannot_access_service_management(self):
		client_user = User.objects.create_user(
			username='client-person',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)

		response = self.client.get(reverse('catalog:service_list'))
		self.assertRedirects(response, reverse('accounts:dashboard'))


class ServiceEditTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Sound Healing', slug='sound-healing')
		self.professional_user = User.objects.create_user(
			username='svc-edit-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Edit Studio',
			headline='Editor',
			bio='Bio.',
			modalities='sound healing',
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Original Service',
			description='Original description.',
			duration_minutes=60,
			price_cents=10000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

	def test_professional_can_edit_own_service(self):
		self.client.force_login(self.professional_user)
		response = self.client.post(
			reverse('catalog:service_edit', args=[self.service.pk]),
			{
				'category': self.category.pk,
				'name': 'Updated Service',
				'description': 'Updated description.',
				'duration_minutes': 75,
				'price_cents': 12000,
				'delivery_format': Service.DeliveryFormat.VIRTUAL,
				'is_active': True,
			},
		)
		self.assertRedirects(response, reverse('catalog:service_list'))
		self.service.refresh_from_db()
		self.assertEqual(self.service.name, 'Updated Service')

	def test_professional_cannot_edit_another_pros_service(self):
		other_user = User.objects.create_user(
			username='other-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		other_profile = ProfessionalProfile.objects.create(
			user=other_user,
			business_name='Other Studio',
			headline='Other',
			bio='Bio.',
			modalities='yoga',
		)
		other_service = Service.objects.create(
			professional=other_profile,
			category=self.category,
			name='Other Service',
			description='Desc.',
			duration_minutes=45,
			price_cents=8000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)
		self.client.force_login(self.professional_user)
		response = self.client.get(reverse('catalog:service_edit', args=[other_service.pk]))
		self.assertEqual(response.status_code, 404)

	def test_client_cannot_edit_service(self):
		client_user = User.objects.create_user(
			username='svc-client',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)
		response = self.client.get(reverse('catalog:service_edit', args=[self.service.pk]))
		self.assertRedirects(response, reverse('accounts:dashboard'))


class PreviewSeedCommandTests(TestCase):
	def test_seed_preview_data_is_idempotent(self):
		call_command('seed_preview_data')
		first_profile_count = ProfessionalProfile.objects.filter(is_visible=True).count()
		first_service_count = Service.objects.count()

		call_command('seed_preview_data')
		second_profile_count = ProfessionalProfile.objects.filter(is_visible=True).count()
		second_service_count = Service.objects.count()

		self.assertEqual(first_profile_count, second_profile_count)
		self.assertEqual(first_service_count, second_service_count)

	def test_seed_preview_data_clear_rebuilds(self):
		call_command('seed_preview_data')
		count_after_seed = Service.objects.count()

		call_command('seed_preview_data', clear=True)
		count_after_clear_seed = Service.objects.count()

		self.assertGreater(count_after_seed, 0)
		self.assertEqual(count_after_seed, count_after_clear_seed)

	def test_seed_marketing_dataset_creates_larger_profile_set(self):
		call_command('seed_preview_data', dataset='preview', clear=True)
		preview_profile_count = ProfessionalProfile.objects.filter(is_visible=True).count()

		call_command('seed_preview_data', dataset='marketing', clear=True)
		marketing_profile_count = ProfessionalProfile.objects.filter(
			user__username__startswith='marketing_',
			is_visible=True,
		).count()

		self.assertGreaterEqual(marketing_profile_count, 20)
		self.assertGreater(marketing_profile_count, preview_profile_count)

	def test_seed_marketing_dataset_is_idempotent(self):
		call_command('seed_preview_data', dataset='marketing', clear=True)
		first_marketing_service_count = Service.objects.filter(
			professional__user__username__startswith='marketing_'
		).count()

		call_command('seed_preview_data', dataset='marketing')
		second_marketing_service_count = Service.objects.filter(
			professional__user__username__startswith='marketing_'
		).count()

		self.assertEqual(first_marketing_service_count, second_marketing_service_count)
