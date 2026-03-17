from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.moderation.models import ModerationDecision

from .models import ProfessionalProfile


class ProfessionalOnboardingTests(TestCase):
	def test_only_professionals_can_access_onboarding(self):
		client_user = User.objects.create_user(
			username='client_user',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)

		response = self.client.get(reverse('professionals:onboarding'))
		self.assertRedirects(response, reverse('accounts:dashboard'))

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

		self.assertRedirects(response, reverse('accounts:dashboard'))
		profile = ProfessionalProfile.objects.get(user=professional_user)
		self.assertEqual(
			profile.approval_status,
			ProfessionalProfile.ApprovalStatus.PENDING,
		)
		self.assertFalse(profile.is_visible)


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
				'modalities': 'sound healing',
				'location': 'Denver',
				'is_virtual': True,
				'years_experience': 3,
				'profile_image_url': '',
			},
		)
		self.assertRedirects(response, reverse('accounts:dashboard'))
		self.profile.refresh_from_db()
		self.assertEqual(self.profile.business_name, 'Updated Name')

	def test_client_cannot_access_profile_edit(self):
		client_user = User.objects.create_user(
			username='cl-edit',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)
		self.client.force_login(client_user)
		response = self.client.get(reverse('professionals:profile_edit'))
		self.assertRedirects(response, reverse('accounts:dashboard'))



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
