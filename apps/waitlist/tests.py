from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import PractitionerWaitlistProfile, StatusTransition


class WaitlistLandingTests(TestCase):
    def test_landing_renders_service_explanations(self):
        response = self.client.get(reverse('waitlist:landing'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Service tracks we are launching first')
        self.assertContains(response, 'Wellness Practitioners')
        self.assertContains(response, 'Spiritual Guides')

    def test_practitioner_can_join_waitlist(self):
        response = self.client.post(
            reverse('waitlist:landing'),
            {
                'full_name': 'Ari Sage',
                'email': 'ari@example.com',
                'business_name': 'Sage Studio',
                'headline': 'Trauma-informed energy practitioner',
                'modalities': 'reiki, meditation',
                'practice_type': PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
                'location': 'Portland',
                'is_virtual': True,
                'offers_in_person': True,
                'years_experience': 6,
                'website_url': 'https://example.com',
                'notes': 'Interested in early beta access.',
            },
            follow=False,
        )

        self.assertRedirects(
            response,
            f"{reverse('waitlist:landing')}?submitted=1",
            fetch_redirect_response=False,
        )

        follow_response = self.client.get(response['Location'])
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, 'You are on the waitlist.')
        self.assertTrue(PractitionerWaitlistProfile.objects.filter(email='ari@example.com').exists())

    def test_submitted_query_param_renders_page(self):
        response = self.client.get(f"{reverse('waitlist:landing')}?submitted=1")

        self.assertEqual(response.status_code, 200)

    def test_practitioner_can_join_waitlist_without_business_name(self):
        response = self.client.post(
            reverse('waitlist:landing'),
            {
                'full_name': 'Solo Healer',
                'email': 'solo@example.com',
                'business_name': '',
                'headline': 'Independent practitioner',
                'modalities': 'energy work',
                'practice_type': PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
                'location': 'Remote',
                'is_virtual': True,
                'offers_in_person': False,
                'years_experience': 4,
                'website_url': '',
                'notes': '',
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(PractitionerWaitlistProfile.objects.filter(email='solo@example.com').exists())

    def test_at_least_one_delivery_format_is_required(self):
        response = self.client.post(
            reverse('waitlist:landing'),
            {
                'full_name': 'Ari Sage',
                'email': 'ari+format@example.com',
                'business_name': 'Sage Studio',
                'headline': 'Trauma-informed energy practitioner',
                'modalities': 'reiki, meditation',
                'practice_type': PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
                'location': 'Portland',
                'years_experience': 6,
                'website_url': 'https://example.com',
                'notes': 'Interested in early beta access.',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select at least one session format: virtual or in-person.')

    def test_duplicate_email_is_rejected(self):
        PractitionerWaitlistProfile.objects.create(
            full_name='Ari Sage',
            email='ari@example.com',
            business_name='Sage Studio',
            headline='Practitioner',
            modalities='reiki',
            practice_type=PractitionerWaitlistProfile.PracticeType.SPIRITUAL,
        )

        response = self.client.post(
            reverse('waitlist:landing'),
            {
                'full_name': 'Ari Sage',
                'email': 'ari@example.com',
                'business_name': 'Sage Studio 2',
                'headline': 'Another profile',
                'modalities': 'sound healing',
                'practice_type': PractitionerWaitlistProfile.PracticeType.WELLNESS,
                'location': '',
                'is_virtual': True,
                'offers_in_person': False,
                'years_experience': 3,
                'website_url': '',
                'notes': '',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This email is already on the waitlist.')

    def test_signup_sends_confirmation_email(self):
        self.client.post(
            reverse('waitlist:landing'),
            {
                'full_name': 'Mira Bell',
                'email': 'mira@example.com',
                'business_name': 'Bell Practice',
                'headline': 'Somatic therapist',
                'modalities': 'somatic, breathwork',
                'practice_type': PractitionerWaitlistProfile.PracticeType.WELLNESS,
                'location': 'Austin',
                'is_virtual': True,
                'offers_in_person': False,
                'years_experience': 3,
                'website_url': '',
                'notes': '',
            },
        )

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn('mira@example.com', msg.to)
        self.assertIn('verify', msg.subject.lower())
        self.assertIn('Mira Bell', msg.body)

    def test_new_signup_status_defaults_to_new(self):
        PractitionerWaitlistProfile.objects.create(
            full_name='Dana Lee',
            email='dana@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
            is_virtual=True,
        )
        profile = PractitionerWaitlistProfile.objects.get(email='dana@example.com')
        self.assertEqual(profile.status, PractitionerWaitlistProfile.Status.NEW)

    def test_status_changed_at_updates_on_status_transition(self):
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Status Change',
            email='status-change@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
        )
        before_change = profile.status_changed_at

        profile.status = PractitionerWaitlistProfile.Status.REVIEWING
        profile.save(update_fields=['status'])
        profile.refresh_from_db()

        self.assertEqual(profile.status, PractitionerWaitlistProfile.Status.REVIEWING)
        self.assertGreaterEqual(profile.status_changed_at, before_change)
        self.assertLess((timezone.now() - profile.status_changed_at).total_seconds(), 5)

    def test_status_transition_created_on_status_change(self):
        """Verify that a StatusTransition record is created when a profile's status changes."""
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Transition Test',
            email='transition@example.com',
            headline='Therapist',
            modalities='therapy',
            practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
        )
        
        # Initial status is NEW, so no transitions yet
        self.assertEqual(StatusTransition.objects.filter(profile=profile).count(), 0)
        
        # Transition to REVIEWING
        profile.status = PractitionerWaitlistProfile.Status.REVIEWING
        profile.save()
        
        # Verify transition record created
        transitions = StatusTransition.objects.filter(profile=profile)
        self.assertEqual(transitions.count(), 1)
        
        t = transitions.first()
        self.assertEqual(t.from_status, PractitionerWaitlistProfile.Status.NEW)
        self.assertEqual(t.to_status, PractitionerWaitlistProfile.Status.REVIEWING)
        self.assertIsNone(t.changed_by)  # No user set when saved via model
    
    def test_multiple_transitions_tracked(self):
        """Verify multiple transitions are all tracked."""
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Multi Transition',
            email='multi-transition@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
        )
        
        # Transition 1: NEW → REVIEWING
        profile.status = PractitionerWaitlistProfile.Status.REVIEWING
        profile.save()
        
        # Transition 2: REVIEWING → INVITED
        profile.status = PractitionerWaitlistProfile.Status.INVITED
        profile.save()
        
        # Verify both transitions recorded
        transitions = list(profile.status_transitions.all().order_by('changed_at'))
        self.assertEqual(len(transitions), 2)
        
        self.assertEqual(transitions[0].from_status, PractitionerWaitlistProfile.Status.NEW)
        self.assertEqual(transitions[0].to_status, PractitionerWaitlistProfile.Status.REVIEWING)
        
        self.assertEqual(transitions[1].from_status, PractitionerWaitlistProfile.Status.REVIEWING)
        self.assertEqual(transitions[1].to_status, PractitionerWaitlistProfile.Status.INVITED)
    
    def test_transition_stores_user(self):
        """Verify StatusTransition can store which user made the change (via admin action)."""
        from apps.accounts.models import User
        
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Admin Action Test',
            email='admin-action@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
        )
        
        admin_user = User.objects.create_user(
            username='admin',
            email='admin@example.com',
            password='testpass',
            role=User.Role.ADMIN,
        )
        
        # Create transition with changed_by user
        t = StatusTransition.objects.create(
            profile=profile,
            from_status=PractitionerWaitlistProfile.Status.NEW,
            to_status=PractitionerWaitlistProfile.Status.REVIEWING,
            changed_at=timezone.now(),
            changed_by=admin_user,
        )
        
        t.refresh_from_db()
        self.assertEqual(t.changed_by, admin_user)

    def test_mark_as_invited_action_creates_transitions(self):
        """Verify that the mark_as_invited admin action creates StatusTransition records."""
        from apps.accounts.models import User
        from .admin import mark_as_invited
        from unittest.mock import Mock
        
        # Create test profiles
        profile1 = PractitionerWaitlistProfile.objects.create(
            full_name='Profile 1',
            email='profile1@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
            status=PractitionerWaitlistProfile.Status.REVIEWING,
        )
        
        profile2 = PractitionerWaitlistProfile.objects.create(
            full_name='Profile 2',
            email='profile2@example.com',
            headline='Therapist',
            modalities='therapy',
            practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
            status=PractitionerWaitlistProfile.Status.REVIEWING,
        )
        
        # Create admin user
        admin_user = User.objects.create_user(
            username='admin_marker',
            email='admin_marker@example.com',
            password='testpass',
            role=User.Role.ADMIN,
        )
        
        # Create mock request with user attribute
        request = Mock()
        request.user = admin_user
        
        # Build mock modeladmin
        from .admin import PractitionerWaitlistProfileAdmin
        from django.contrib.admin.sites import AdminSite
        
        admin_site = AdminSite()
        model_admin = PractitionerWaitlistProfileAdmin(PractitionerWaitlistProfile, admin_site)
        model_admin.message_user = Mock()  # Mock the message_user method to avoid middleware
        
        # Call the action
        queryset = PractitionerWaitlistProfile.objects.filter(status=PractitionerWaitlistProfile.Status.REVIEWING)
        mark_as_invited(model_admin, request, queryset)
        
        # Verify status updated
        profile1.refresh_from_db()
        profile2.refresh_from_db()
        self.assertEqual(profile1.status, PractitionerWaitlistProfile.Status.INVITED)
        self.assertEqual(profile2.status, PractitionerWaitlistProfile.Status.INVITED)
        
        # Verify transitions created with changed_by set
        t1 = StatusTransition.objects.filter(profile=profile1).first()
        t2 = StatusTransition.objects.filter(profile=profile2).first()
        
        self.assertIsNotNone(t1)
        self.assertIsNotNone(t2)
        self.assertEqual(t1.changed_by, admin_user)
        self.assertEqual(t2.changed_by, admin_user)
        self.assertEqual(t1.to_status, PractitionerWaitlistProfile.Status.INVITED)
        self.assertEqual(t2.to_status, PractitionerWaitlistProfile.Status.INVITED)

    def test_status_change_sends_notification_email(self):
        """Verify that status transitions trigger notification emails."""
        from apps.waitlist.emails import send_status_change_notification
        
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Email Test',
            email='emailtest@example.com',
            headline='Coach',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
        )
        
        # Create a transition to REVIEWING
        transition = StatusTransition.objects.create(
            profile=profile,
            from_status=PractitionerWaitlistProfile.Status.NEW,
            to_status=PractitionerWaitlistProfile.Status.REVIEWING,
            changed_at=timezone.now(),
        )
        
        # Send notification
        send_status_change_notification(transition)
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn('emailtest@example.com', msg.to)
        self.assertIn('under review', msg.subject.lower())
    
    def test_invited_status_email_includes_login_link(self):
        """Verify invited status email has login instructions."""
        from apps.waitlist.emails import send_status_change_notification
        
        profile = PractitionerWaitlistProfile.objects.create(
            full_name='Invited Test',
            email='invited@example.com',
            headline='Therapist',
            modalities='therapy',
            practice_type=PractitionerWaitlistProfile.PracticeType.WELLNESS,
        )
        
        transition = StatusTransition.objects.create(
            profile=profile,
            from_status=PractitionerWaitlistProfile.Status.REVIEWING,
            to_status=PractitionerWaitlistProfile.Status.INVITED,
            changed_at=timezone.now(),
        )
        
        send_status_change_notification(transition)
        
        msg = mail.outbox[0]
        self.assertIn('invited', msg.subject.lower())
        self.assertIn('portal', msg.body.lower())
