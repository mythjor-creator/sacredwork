from django.test import TestCase
from django.urls import reverse

from apps.billing.models import ProfessionalSubscription
from apps.accounts.models import User
from apps.moderation.models import ModerationDecision
from apps.waitlist.models import PractitionerWaitlistProfile

from .models import ProfessionalCredential, ProfessionalProfile


class ProfessionalOnboardingTests(TestCase):
	def test_only_professionals_can_access_onboarding(self):
		client_user = User.objects.create_user(
			username='client_user',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)

		response = self.client.get(reverse('professionals:onboarding'))
		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

	def test_professional_can_submit_onboarding(self):
		professional_user = User.objects.create_user(
			username='pro_user',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.client.force_login(professional_user)

		response = self.client.post(
			reverse('professionals:onboarding'),
			{
				'business_name': 'Sacred Space Healing',
				'headline': 'Holistic energy practitioner',
				'bio': 'I offer reiki and mindfulness sessions.',
				'modalities': 'reiki, breathwork',
				'location': 'Portland',
				'is_virtual': True,
				'years_experience': 4,
				'profile_image_url': 'https://example.com/profile.jpg',
			},
		)

		self.assertRedirects(response, reverse('professionals:profile_core'))
		profile = ProfessionalProfile.objects.get(user=professional_user)
		self.assertEqual(
			profile.approval_status,
			ProfessionalProfile.ApprovalStatus.PENDING,
		)
		self.assertFalse(profile.is_visible)

	def test_professional_can_submit_onboarding_without_business_name(self):
		professional_user = User.objects.create_user(
			username='solo_pro_user',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.client.force_login(professional_user)

		response = self.client.post(
			reverse('professionals:onboarding'),
			{
				'business_name': '',
				'headline': 'Solo wellness practitioner',
				'bio': 'I offer private sessions.',
				'modalities': 'mindfulness, breathwork',
				'location': 'Remote',
				'is_virtual': True,
				'years_experience': 5,
				'profile_image_url': '',
			},
		)

		self.assertRedirects(response, reverse('professionals:profile_core'))
		profile = ProfessionalProfile.objects.get(user=professional_user)
		self.assertEqual(profile.business_name, '')
		self.assertEqual(profile.display_name, professional_user.username)

	def test_onboarding_page_shows_continue_setup_cta(self):
		professional_user = User.objects.create_user(
			username='cta_pro_user',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.client.force_login(professional_user)

		response = self.client.get(reverse('professionals:onboarding'))
		self.assertContains(response, 'Continue setup')
		self.assertContains(response, 'Core profile')


class ProfileEditTests(TestCase):
	def setUp(self):
		self.professional_user = User.objects.create_user(
			username='edit-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Original Name',
			headline='Original headline',
			bio='Original bio.',
			modalities='reiki',
		)

	def test_professional_can_update_profile(self):
		self.client.force_login(self.professional_user)
		response = self.client.post(
			reverse('professionals:profile_edit'),
			{
				'business_name': 'Updated Name',
				'headline': 'Updated headline',
				'bio': 'Updated bio.',
				'long_bio': 'Long form story for deeper context.',
				'modalities': 'sound healing',
				'location': 'Denver',
				'is_virtual': True,
				'years_experience': 3,
				'profile_image_url': '',
				'gallery-TOTAL_FORMS': '1',
				'gallery-INITIAL_FORMS': '0',
				'gallery-MIN_NUM_FORMS': '0',
				'gallery-MAX_NUM_FORMS': '1000',
				'gallery-0-caption': '',
				'gallery-0-sort_order': '0',
				'gallery-0-is_active': 'on',
				'credentials-TOTAL_FORMS': '1',
				'credentials-INITIAL_FORMS': '0',
				'credentials-MIN_NUM_FORMS': '0',
				'credentials-MAX_NUM_FORMS': '1000',
				'credentials-0-credential_type': ProfessionalCredential.CredentialType.CERTIFICATION,
				'credentials-0-title': 'Certified Breathwork Facilitator',
				'credentials-0-organization': 'Sacred Institute',
				'credentials-0-license_number': '',
				'credentials-0-issued_on': '',
				'credentials-0-expires_on': '',
				'credentials-0-verification_url': '',
				'credentials-0-notes': '',
				'credentials-0-sort_order': '0',
				'credentials-0-is_active': 'on',
			},
		)
		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)
		self.profile.refresh_from_db()
		self.assertEqual(self.profile.business_name, 'Updated Name')
		self.assertEqual(self.profile.long_bio, 'Long form story for deeper context.')
		self.assertEqual(self.profile.credentials.count(), 1)

	def test_credential_validation_blocks_bad_expiration_date(self):
		self.client.force_login(self.professional_user)
		response = self.client.post(
			reverse('professionals:profile_edit'),
			{
				'business_name': 'Original Name',
				'headline': 'Original headline',
				'bio': 'Original bio.',
				'long_bio': '',
				'modalities': 'reiki',
				'location': '',
				'is_virtual': True,
				'years_experience': 0,
				'profile_image_url': '',
				'gallery-TOTAL_FORMS': '1',
				'gallery-INITIAL_FORMS': '0',
				'gallery-MIN_NUM_FORMS': '0',
				'gallery-MAX_NUM_FORMS': '1000',
				'gallery-0-caption': '',
				'gallery-0-sort_order': '0',
				'credentials-TOTAL_FORMS': '1',
				'credentials-INITIAL_FORMS': '0',
				'credentials-MIN_NUM_FORMS': '0',
				'credentials-MAX_NUM_FORMS': '1000',
				'credentials-0-credential_type': ProfessionalCredential.CredentialType.LICENSE,
				'credentials-0-title': 'License Test',
				'credentials-0-organization': 'Board',
				'credentials-0-license_number': 'ABC-123',
				'credentials-0-issued_on': '2025-01-01',
				'credentials-0-expires_on': '2024-01-01',
				'credentials-0-verification_url': '',
				'credentials-0-notes': '',
				'credentials-0-sort_order': '0',
			},
		)
		self.assertEqual(response.status_code, 200)
		self.assertContains(response, 'Expiration date must be after issued date.')

	def test_client_cannot_access_profile_edit(self):
		client_user = User.objects.create_user(
			username='cl-edit',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)
		response = self.client.get(reverse('professionals:profile_edit'))
		self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)



class ModerationAdminTests(TestCase):
	def setUp(self):
		self.admin_user = User.objects.create_superuser(
			username='staff_admin',
			password='AdminPass123!!',
		)
		pending_user = User.objects.create_user(
			username='pending-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.pending_profile = ProfessionalProfile.objects.create(
			user=pending_user,
			business_name='Pending Studio',
			headline='Awaiting review',
			bio='Bio text here.',
			modalities='breathwork',
			approval_status=ProfessionalProfile.ApprovalStatus.PENDING,
			is_visible=False,
		)
		PractitionerWaitlistProfile.objects.create(
			full_name='Pending Pro',
			email=pending_user.email,
			headline='Founding waitlist record',
			modalities='breathwork',
			practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
			is_virtual=True,
			is_founding_member=True,
		)

	def test_approve_profile_action(self):
		self.client.force_login(self.admin_user)
		change_url = reverse('admin:professionals_professionalprofile_changelist')
		response = self.client.post(
			change_url,
			{'action': 'approve_profiles', '_selected_action': [self.pending_profile.pk]},
		)
		self.assertIn(response.status_code, [200, 302])
		self.pending_profile.refresh_from_db()
		self.assertEqual(self.pending_profile.approval_status, ProfessionalProfile.ApprovalStatus.APPROVED)
		self.assertTrue(self.pending_profile.is_visible)
		self.assertEqual(
			self.pending_profile.subscription_status,
			ProfessionalProfile.SubscriptionStatus.PRELAUNCH,
		)
		subscription = ProfessionalSubscription.objects.get(professional=self.pending_profile)
		self.assertEqual(subscription.status, ProfessionalSubscription.Status.PENDING_LAUNCH)
		self.assertTrue(subscription.founding_member_rate_locked)
		self.assertIsNotNone(subscription.plan)
		self.assertEqual(subscription.plan.code, 'founding-annual')
		self.assertTrue(
			ModerationDecision.objects.filter(
				profile=self.pending_profile,
				decided_by=self.admin_user,
				decision=ModerationDecision.Decision.APPROVED,
			).exists()
		)

	def test_reject_profile_action(self):
		self.client.force_login(self.admin_user)
		change_url = reverse('admin:professionals_professionalprofile_changelist')
		response = self.client.post(
			change_url,
			{'action': 'reject_profiles', '_selected_action': [self.pending_profile.pk]},
		)
		self.assertIn(response.status_code, [200, 302])
		self.pending_profile.refresh_from_db()
		self.assertEqual(self.pending_profile.approval_status, ProfessionalProfile.ApprovalStatus.REJECTED)
		self.assertFalse(self.pending_profile.is_visible)
		self.assertTrue(
			ModerationDecision.objects.filter(
				profile=self.pending_profile,
				decision=ModerationDecision.Decision.REJECTED,
			).exists()
		)


class ProfessionalBillingStateTests(TestCase):
	def test_prelaunch_status_grants_billing_access(self):
		user = User.objects.create_user(
			username='billing-state-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		profile = ProfessionalProfile.objects.create(
			user=user,
			business_name='Access Studio',
			headline='Billing access profile',
			bio='Used to test billing access.',
			modalities='reiki',
			subscription_status=ProfessionalProfile.SubscriptionStatus.PRELAUNCH,
		)

		self.assertTrue(profile.billing_access_granted)

	def test_not_started_status_does_not_grant_billing_access(self):
		user = User.objects.create_user(
			username='billing-state-none',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		profile = ProfessionalProfile.objects.create(
			user=user,
			business_name='No Access Studio',
			headline='No billing access profile',
			bio='Used to test missing billing access.',
			modalities='coaching',
		)

		self.assertFalse(profile.billing_access_granted)
