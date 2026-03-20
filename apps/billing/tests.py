from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile


class BillingOverviewTests(TestCase):
    def test_client_is_redirected_away_from_billing_overview(self):
        user = User.objects.create_user(
            username='billing-client',
            password='StrongPass123!!',
            role=User.Role.CLIENT,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('billing:overview'))

        self.assertRedirects(response, reverse('accounts:dashboard'), fetch_redirect_response=False)

    def test_professional_can_view_billing_overview(self):
        user = User.objects.create_user(
            username='billing-pro',
            password='StrongPass123!!',
            role=User.Role.PROFESSIONAL,
        )
        profile = ProfessionalProfile.objects.create(
            user=user,
            business_name='Billing Studio',
            headline='Billing profile',
            bio='Profile used for billing overview tests.',
            modalities='coaching',
            subscription_status=ProfessionalProfile.SubscriptionStatus.PRELAUNCH,
        )
        self.client.force_login(user)

        response = self.client.get(reverse('billing:overview'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, profile.display_name)
        self.assertContains(response, 'Prelaunch Access')
