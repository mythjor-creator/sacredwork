from datetime import timedelta

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import User
from apps.professionals.models import ProfessionalCredential, ProfessionalProfile, ProfileGalleryImage
from apps.waitlist.models import PractitionerWaitlistProfile

from .models import AnalyticsEvent, Category, Service, ServiceTier


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
		self.assertContains(response, '1 practitioner found')
		self.assertContains(response, 'Query: reiki')
		self.assertContains(response, 'Category: Energy Work')
		self.assertContains(response, 'Clear filters')

	def test_marketplace_results_count_visible_without_filters(self):
		response = self.client.get(reverse('catalog:marketplace'))

		self.assertContains(response, '1 practitioner found')

	def test_marketplace_can_filter_virtual_only(self):
		in_person_user = User.objects.create_user(
			username='in-person-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		in_person_profile = ProfessionalProfile.objects.create(
			user=in_person_user,
			business_name='In Person Studio',
			headline='In person only sessions',
			bio='In person support.',
			modalities='coaching',
			location='Austin',
			is_virtual=False,
			years_experience=4,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		Service.objects.create(
			professional=in_person_profile,
			category=self.category,
			name='Studio Session',
			description='In office support.',
			duration_minutes=60,
			price_cents=11000,
			delivery_format=Service.DeliveryFormat.IN_PERSON,
		)

		response = self.client.get(reverse('catalog:marketplace'), {'virtual': '1'})

		self.assertContains(response, 'Visible Healing Studio')
		self.assertNotContains(response, 'In Person Studio')
		self.assertContains(response, 'Virtual only')

	def test_marketplace_sort_desc_orders_results_by_name(self):
		another_user = User.objects.create_user(
			username='alpha-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		another_profile = ProfessionalProfile.objects.create(
			user=another_user,
			business_name='A Aligned Studio',
			headline='Support profile',
			bio='Helpful support.',
			modalities='breathwork',
			location='Portland',
			is_virtual=True,
			years_experience=3,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		Service.objects.create(
			professional=another_profile,
			category=self.category,
			name='Aligned Session',
			description='Virtual session.',
			duration_minutes=45,
			price_cents=9500,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

		response = self.client.get(reverse('catalog:marketplace'), {'sort': 'name_desc'})

		self.assertContains(response, 'Sort: Name (Z-A)')
		self.assertContains(response, 'Visible Healing Studio', html=False)
		self.assertContains(response, 'A Aligned Studio', html=False)
		self.assertContains(
			response,
			'Visible Healing Studio',
			html=False,
		)
		self.assertTrue(
			response.content.decode().find('Visible Healing Studio')
			< response.content.decode().find('A Aligned Studio')
		)

	def test_marketplace_preview_badge_shows_only_in_sample_mode(self):
		response_without_sample = self.client.get(reverse('catalog:marketplace'))
		self.assertNotContains(response_without_sample, 'Preview mode: sample data')

		with override_settings(DEBUG=True):
			response_with_sample = self.client.get(reverse('catalog:marketplace'), {'sample': '1'})
		self.assertContains(response_with_sample, 'Preview mode: sample data')

	@override_settings(ENFORCE_PRACTITIONER_BILLING_ACCESS=True)
	def test_marketplace_hides_profiles_without_billing_access_when_enforced(self):
		self.visible_profile.subscription_status = ProfessionalProfile.SubscriptionStatus.NOT_STARTED
		self.visible_profile.save(update_fields=['subscription_status', 'updated_at'])

		response = self.client.get(reverse('catalog:marketplace'))

		self.assertEqual(response.status_code, 200)
		self.assertNotContains(response, 'Visible Healing Studio')

	@override_settings(ENFORCE_PRACTITIONER_BILLING_ACCESS=True)
	def test_marketplace_shows_active_subscription_profiles_when_enforced(self):
		self.visible_profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
		self.visible_profile.save(update_fields=['subscription_status', 'updated_at'])

		response = self.client.get(reverse('catalog:marketplace'))

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Visible Healing Studio')


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
				'tiers-TOTAL_FORMS': '1',
				'tiers-INITIAL_FORMS': '0',
				'tiers-MIN_NUM_FORMS': '0',
				'tiers-MAX_NUM_FORMS': '1000',
				'tiers-0-name': 'Standard',
				'tiers-0-description': 'Core tier',
				'tiers-0-duration_minutes': '75',
				'tiers-0-price_cents': '15000',
				'tiers-0-sort_order': '0',
				'tiers-0-is_active': 'on',
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
		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

	def test_service_create_blocks_duplicate_tier_names(self):
		self.client.force_login(self.professional_user)

		response = self.client.post(
			reverse('catalog:service_create'),
			{
				'category': self.category.pk,
				'name': 'Tiered Session',
				'description': 'A service with duplicate tiers.',
				'duration_minutes': 60,
				'price_cents': 10000,
				'delivery_format': Service.DeliveryFormat.VIRTUAL,
				'is_active': True,
				'tiers-TOTAL_FORMS': '2',
				'tiers-INITIAL_FORMS': '0',
				'tiers-MIN_NUM_FORMS': '0',
				'tiers-MAX_NUM_FORMS': '1000',
				'tiers-0-name': 'Standard',
				'tiers-0-description': 'Core tier',
				'tiers-0-duration_minutes': '60',
				'tiers-0-price_cents': '10000',
				'tiers-0-sort_order': '0',
				'tiers-0-is_active': 'on',
				'tiers-1-name': 'standard',
				'tiers-1-description': 'Duplicate label',
				'tiers-1-duration_minutes': '90',
				'tiers-1-price_cents': '15000',
				'tiers-1-sort_order': '1',
				'tiers-1-is_active': 'on',
			},
		)

		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Tier names must be unique within a service.')
		self.assertFalse(self.profile.services.filter(name='Tiered Session').exists())


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
				'tiers-TOTAL_FORMS': '1',
				'tiers-INITIAL_FORMS': '0',
				'tiers-MIN_NUM_FORMS': '0',
				'tiers-MAX_NUM_FORMS': '1000',
				'tiers-0-name': 'Intensive Tier',
				'tiers-0-description': 'Long session option',
				'tiers-0-duration_minutes': '105',
				'tiers-0-price_cents': '18000',
				'tiers-0-sort_order': '0',
				'tiers-0-is_active': 'on',
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
		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

	def test_professional_can_delete_existing_tier_on_edit(self):
		tier = ServiceTier.objects.create(
			service=self.service,
			name='Standard',
			description='Default tier',
			price_cents=10000,
			duration_minutes=60,
		)
		self.client.force_login(self.professional_user)
		response = self.client.post(
			reverse('catalog:service_edit', args=[self.service.pk]),
			{
				'category': self.category.pk,
				'name': 'Original Service',
				'description': 'Original description.',
				'duration_minutes': 60,
				'price_cents': 10000,
				'delivery_format': Service.DeliveryFormat.VIRTUAL,
				'is_active': True,
				'tiers-TOTAL_FORMS': '1',
				'tiers-INITIAL_FORMS': '1',
				'tiers-MIN_NUM_FORMS': '0',
				'tiers-MAX_NUM_FORMS': '1000',
				'tiers-0-id': str(tier.pk),
				'tiers-0-name': 'Standard',
				'tiers-0-description': 'Default tier',
				'tiers-0-duration_minutes': '60',
				'tiers-0-price_cents': '10000',
				'tiers-0-sort_order': '0',
				'tiers-0-is_active': 'on',
				'tiers-0-DELETE': 'on',
			},
		)

		self.assertRedirects(response, reverse('catalog:service_list'))
		self.assertFalse(ServiceTier.objects.filter(pk=tier.pk).exists())


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


class AnalyticsEventTests(TestCase):
	def test_track_endpoint_persists_supported_event(self):
		response = self.client.post(
			reverse('catalog:analytics_track'),
			data='{"event":"search_submitted","payload":{"source":"home","has_query":true,"has_category":false},"path":"/"}',
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertTrue(
			AnalyticsEvent.objects.filter(name='search_submitted', source='home', path='/').exists()
		)

	def test_track_endpoint_rejects_unknown_event(self):
		response = self.client.post(
			reverse('catalog:analytics_track'),
			data='{"event":"unexpected_event","payload":{},"path":"/"}',
			content_type='application/json',
		)

		self.assertEqual(response.status_code, 400)
		self.assertEqual(AnalyticsEvent.objects.count(), 0)

	def test_staff_can_view_kpi_dashboard(self):
		staff_user = User.objects.create_user(
			username='kpi-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/')
		AnalyticsEvent.objects.create(name='profile_viewed', source='professional_detail', path='/professionals/1/')

		response = self.client.get(reverse('catalog:analytics_kpis'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Analytics KPI Snapshot')
		self.assertContains(response, 'Search submits')

	def test_non_staff_cannot_view_kpi_dashboard(self):
		normal_user = User.objects.create_user(
			username='kpi-user',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(normal_user)

		response = self.client.get(reverse('catalog:analytics_kpis'))
		self.assertEqual(response.status_code, 302)

	def test_kpi_dashboard_respects_days_filter(self):
		staff_user = User.objects.create_user(
			username='kpi-filter-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		recent_event = AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/')
		old_event = AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/old')
		old_event.created_at = timezone.now() - timedelta(days=20)
		old_event.save(update_fields=['created_at'])

		response = self.client.get(reverse('catalog:analytics_kpis'), {'days': '14'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Last 14 days')
		self.assertContains(response, recent_event.path)
		self.assertNotContains(response, old_event.path)

	def test_kpi_dashboard_csv_export(self):
		staff_user = User.objects.create_user(
			username='kpi-csv-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)
		AnalyticsEvent.objects.create(name='profile_viewed', source='professional_detail', path='/professionals/12/')

		response = self.client.get(reverse('catalog:analytics_kpis'), {'days': '7', 'format': 'csv'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response['Content-Type'], 'text/csv')
		self.assertIn('clairbook-analytics-7d.csv', response['Content-Disposition'])

	def test_kpi_dashboard_supports_this_week_preset(self):
		staff_user = User.objects.create_user(
			username='kpi-this-week-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		recent = AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/')
		old = AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/last-week')
		old.created_at = timezone.now() - timedelta(days=10)
		old.save(update_fields=['created_at'])

		response = self.client.get(reverse('catalog:analytics_kpis'), {'preset': 'this_week'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'This week from')
		self.assertContains(response, recent.path)
		self.assertNotContains(response, old.path)

	def test_kpi_dashboard_shows_source_breakdown(self):
		staff_user = User.objects.create_user(
			username='kpi-breakdown-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/')
		AnalyticsEvent.objects.create(name='search_submitted', source='discover', path='/browse/')
		AnalyticsEvent.objects.create(name='search_submitted', source='home', path='/')

		response = self.client.get(reverse('catalog:analytics_kpis'), {'days': '7'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Source breakdown')
		self.assertContains(response, '<strong>home</strong>: 2', html=True)
		self.assertContains(response, '<strong>discover</strong>: 1', html=True)

	def test_kpi_dashboard_shows_operational_shortcuts(self):
		staff_user = User.objects.create_user(
			username='kpi-ops-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		response = self.client.get(reverse('catalog:analytics_kpis'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Operational shortcuts')

		new_waitlist_link = (
			reverse('admin:waitlist_practitionerwaitlistprofile_changelist') + '?status__exact=new'
		)
		unverified_link = (
			reverse('admin:professionals_professionalprofile_changelist')
			+ '?approval_status__exact=approved&is_verified__exact=0'
		)
		self.assertContains(response, new_waitlist_link)
		self.assertContains(response, unverified_link.replace('&', '&amp;'))

	def test_kpi_dashboard_shows_waitlist_status_aging(self):
		staff_user = User.objects.create_user(
			username='kpi-aging-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		new_profile = PractitionerWaitlistProfile.objects.create(
			full_name='Ari New',
			email='ari-new@example.com',
			headline='Practitioner',
			modalities='reiki',
			practice_type=PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
			status=PractitionerWaitlistProfile.Status.NEW,
		)
		reviewing_profile = PractitionerWaitlistProfile.objects.create(
			full_name='Ari Reviewing',
			email='ari-reviewing@example.com',
			headline='Practitioner',
			modalities='coaching',
			practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
			status=PractitionerWaitlistProfile.Status.REVIEWING,
		)
		new_profile.created_at = timezone.now() - timedelta(days=4)
		reviewing_profile.created_at = timezone.now() - timedelta(days=9)
		new_profile.save(update_fields=['created_at'])
		reviewing_profile.save(update_fields=['created_at'])

		response = self.client.get(reverse('catalog:analytics_kpis'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Waitlist status aging')
		self.assertContains(response, 'New')
		self.assertContains(response, 'Reviewing')
		self.assertContains(response, 'Avg age:')

	def test_kpi_dashboard_csv_includes_status_aging_rows(self):
		staff_user = User.objects.create_user(
			username='kpi-aging-csv-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		PractitionerWaitlistProfile.objects.create(
			full_name='Ari Invited',
			email='ari-invited@example.com',
			headline='Practitioner',
			modalities='breathwork',
			practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
			status=PractitionerWaitlistProfile.Status.INVITED,
		)

		response = self.client.get(reverse('catalog:analytics_kpis'), {'days': '7', 'format': 'csv'})
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'waitlist_status,count,avg_age_days_since_status_change,oldest_age_days_since_status_change')
		self.assertContains(response, 'invited,1')

	def test_kpi_dashboard_status_aging_uses_status_changed_at(self):
		staff_user = User.objects.create_user(
			username='kpi-aging-source-staff',
			password='StrongPass123!!',
			role=User.Role.ADMIN,
			is_staff=True,
		)
		self.client.force_login(staff_user)

		profile = PractitionerWaitlistProfile.objects.create(
			full_name='Ari Shifted',
			email='ari-shifted@example.com',
			headline='Practitioner',
			modalities='reiki',
			practice_type=PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
			status=PractitionerWaitlistProfile.Status.REVIEWING,
		)
		profile.created_at = timezone.now() - timedelta(days=120)
		profile.status_changed_at = timezone.now() - timedelta(days=2)
		profile.save(update_fields=['created_at', 'status_changed_at'])

		response = self.client.get(reverse('catalog:analytics_kpis'))
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Reviewing')
		# If based on created_at this would show ~120 days; this asserts status_changed_at is used.
		self.assertContains(response, 'Avg age: 2.0 days')


class ProfileCredibilityTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Coaching', slug='coaching')
		self.pro_user = User.objects.create_user(
			username='credibility-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.pro_user,
			business_name='Clarity Practice',
			headline='Certified life coach',
			bio='I help people find clarity and direction in their lives through structured coaching.',
			modalities='coaching, NLP',
			location='New York',
			is_virtual=True,
			years_experience=5,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Clarity Session',
			description='A focused 1:1 coaching session.',
			duration_minutes=60,
			price_cents=15000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

	def test_verified_badge_shown_when_is_verified_true(self):
		self.profile.is_verified = True
		self.profile.save()
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertContains(response, 'Verified')

	def test_verified_badge_not_shown_when_is_verified_false(self):
		self.profile.is_verified = False
		self.profile.save()
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertNotContains(response, '✓ Verified')

	def test_completeness_percent_full_profile(self):
		self.profile.profile_image_url = 'https://example.com/photo.jpg'
		self.profile.long_bio = 'Long form biography with practitioner background, process, and outcomes.' * 2
		self.profile.save()
		ProfileGalleryImage.objects.create(
			profile=self.profile,
			image='professionals/gallery/sample.jpg',
			caption='Studio space',
		)
		ProfessionalCredential.objects.create(
			profile=self.profile,
			title='Board Certified Coach',
			credential_type=ProfessionalCredential.CredentialType.CERTIFICATION,
		)
		self.assertEqual(self.profile.completeness_percent, 100)

	def test_completeness_percent_missing_photo(self):
		# Without photo, long bio, gallery, or credentials the score reflects partial setup.
		self.assertEqual(self.profile.completeness_percent, 50)

	def test_completeness_panel_shown_to_profile_owner(self):
		self.client.force_login(self.pro_user)
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertContains(response, 'Profile completeness')

	def test_completeness_panel_hidden_from_other_users(self):
		other = User.objects.create_user(username='anon2', password='StrongPass123!!', role=User.Role.CLIENT)
		self.client.force_login(other)
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertNotContains(response, 'Profile completeness')

	def test_duration_display_under_60_minutes(self):
		self.service.duration_minutes = 45
		self.assertEqual(self.service.duration_display, '45 min')

	def test_duration_display_exact_hour(self):
		self.service.duration_minutes = 60
		self.assertEqual(self.service.duration_display, '1 hr')

	def test_duration_display_multiple_hours(self):
		self.service.duration_minutes = 120
		self.assertEqual(self.service.duration_display, '2 hrs')

	def test_duration_display_hours_and_minutes(self):
		self.service.duration_minutes = 90
		self.assertEqual(self.service.duration_display, '1 hr 30 min')

	def test_service_price_shown_on_profile_page(self):
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertContains(response, '$150.00')

	def test_service_tiers_render_on_profile_page(self):
		ServiceTier.objects.create(
			service=self.service,
			name='Deep Dive Tier',
			description='Extended support and integration notes.',
			price_cents=22000,
			duration_minutes=120,
		)
		response = self.client.get(reverse('catalog:professional_detail', args=[self.profile.pk]))
		self.assertContains(response, 'Deep Dive Tier')
		self.assertContains(response, '$220.00')
