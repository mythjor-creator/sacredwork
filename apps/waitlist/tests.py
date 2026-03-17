from django.test import TestCase
from django.urls import reverse

from .models import PractitionerWaitlistProfile


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
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'You are on the practitioner waitlist.')
        self.assertTrue(PractitionerWaitlistProfile.objects.filter(email='ari@example.com').exists())

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
