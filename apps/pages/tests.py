from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import timedelta

from apps.waitlist.models import PractitionerWaitlistProfile, StatusTransition
from apps.pages.models import EmailVerificationToken, GDPRDataExportLog, GDPRAccountDeletionLog

User = get_user_model()


class PrivacyTermsPages(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='navuser',
            email='navuser@example.com',
            password='TestPass123!!',
            display_name='Nav User',
            role=User.Role.CLIENT,
        )

    def test_healthcheck_renders(self):
        response = self.client.get(reverse('pages:healthcheck'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    @override_settings(DEBUG=False, SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r'^health/$'])
    def test_healthcheck_bypasses_ssl_redirect_in_production(self):
        response = self.client.get(reverse('pages:healthcheck'))
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'status': 'ok'})

    def test_style_sheet_renders(self):
        response = self.client.get(reverse('pages:style_sheet'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Clairbook Style Sheet')

    def test_about_renders(self):
        response = self.client.get(reverse('pages:about'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'About Clairbook')

    def test_about_link_shows_for_authenticated_users(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('pages:pricing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="/about/"', html=False)

    def test_pricing_renders(self):
        response = self.client.get(reverse('pages:pricing'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pricing for practitioners who want room to grow.')
        self.assertContains(response, '60-day free trial')
        self.assertContains(response, '$9.99/month')
        self.assertContains(response, '$24.99/month')
        self.assertContains(response, '$79/year')
        self.assertContains(response, 'href="/waitlist/?tier=basic#waitlist-profile"', html=False)
        self.assertContains(response, 'href="/waitlist/?tier=featured#waitlist-profile"', html=False)
        self.assertContains(response, 'href="/waitlist/?tier=founding#waitlist-profile"', html=False)

    def test_privacy_policy_renders(self):
        response = self.client.get(reverse('pages:privacy'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Privacy Policy')
        self.assertContains(response, 'SacredWork')
    
    def test_terms_renders(self):
        response = self.client.get(reverse('pages:terms'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Terms of Service')


class EmailVerificationTests(TestCase):
    def setUp(self):
        self.profile = PractitionerWaitlistProfile.objects.create(
            full_name='Test Practitioner',
            email='test@example.com',
            headline='Test',
            modalities='test',
            practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
        )
    
    def test_token_created_for_profile(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        self.assertIsNotNone(token.token)
        self.assertIsNone(token.verified_at)
        self.assertTrue(len(token.token) > 40)
    
    def test_token_is_valid_when_fresh(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        self.assertTrue(token.is_valid())
    
    def test_token_invalid_when_verified(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        token.verify()
        self.assertFalse(token.is_valid())
    
    def test_token_expires_after_7_days(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        token.created_at = timezone.now() - timedelta(days=7, hours=1)
        token.save()
        self.assertFalse(token.is_valid())
    
    def test_verify_email_with_valid_token(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        response = self.client.get(reverse('pages:verify_email', args=[token.token]))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email Verified')
        
        token.refresh_from_db()
        self.assertIsNotNone(token.verified_at)
    
    def test_verify_email_with_expired_token(self):
        token = EmailVerificationToken.create_for_profile(self.profile)
        token.created_at = timezone.now() - timedelta(days=8)
        token.save()
        
        response = self.client.get(reverse('pages:verify_email', args=[token.token]))
        
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'expired', status_code=400)
    
    def test_verify_email_with_invalid_token(self):
        response = self.client.get(reverse('pages:verify_email', args=['invalid-token']))
        self.assertEqual(response.status_code, 404)


class GDPRExportTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!!',
            display_name='Test User',
            role=User.Role.CLIENT,
        )
        self.client.force_login(self.user)
    
    def test_gdpr_export_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('pages:gdpr_export'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/accounts/login' in response.url or '/login' in response.url)
    
    def test_gdpr_export_get_shows_form(self):
        response = self.client.get(reverse('pages:gdpr_export'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Download Your Data')
    
    def test_gdpr_export_post_downloads_json(self):
        response = self.client.post(reverse('pages:gdpr_export'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertIn('testuser', response.content.decode())
        
        # Verify log was created
        self.assertEqual(GDPRDataExportLog.objects.filter(user=self.user).count(), 1)
    
    def test_gdpr_export_includes_user_data(self):
        response = self.client.post(reverse('pages:gdpr_export'))
        content = response.content.decode()
        
        self.assertIn('testuser', content)
        self.assertIn('test@example.com', content)
        self.assertIn('Test User', content)


class GDPRDeletionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='delete_user',
            email='delete@example.com',
            password='TestPass123!!',
            role=User.Role.CLIENT,
        )
    
    def test_gdpr_delete_requires_login(self):
        response = self.client.get(reverse('pages:gdpr_delete'))
        self.assertEqual(response.status_code, 302)
    
    def test_gdpr_delete_get_shows_confirmation(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('pages:gdpr_delete'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Delete Your Account')
    
    def test_gdpr_delete_requires_checkbox(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('pages:gdpr_delete'),
            data={},
            follow=True,
        )
        
        # Should still have the user
        self.assertTrue(User.objects.filter(username='delete_user').exists())
    
    def test_gdpr_delete_with_confirmation_deletes_user(self):
        self.client.force_login(self.user)
        user_id = self.user.id
        
        response = self.client.post(
            reverse('pages:gdpr_delete'),
            data={'confirm_delete': 'on'},
            follow=True,
        )
        
        # User should be deleted
        self.assertFalse(User.objects.filter(id=user_id).exists())
        
        # Deletion log should exist
        logs = GDPRAccountDeletionLog.objects.filter(user_identifier__contains='delete_user')
        self.assertEqual(logs.count(), 1)
        self.assertIsNotNone(logs.first().deleted_at)
