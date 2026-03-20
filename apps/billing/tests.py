from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile

from .models import ProfessionalSubscription, SubscriptionPlan


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


class BillingCheckoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='checkout-pro',
            password='StrongPass123!!',
            email='checkout-pro@example.com',
            role=User.Role.PROFESSIONAL,
        )
        self.profile = ProfessionalProfile.objects.create(
            user=self.user,
            business_name='Checkout Studio',
            headline='Checkout profile',
            bio='Profile used for billing checkout tests.',
            modalities='coaching',
            subscription_status=ProfessionalProfile.SubscriptionStatus.PRELAUNCH,
        )
        self.plan = SubscriptionPlan.objects.get(code='founding-annual')
        self.plan.stripe_price_id = 'price_founding_123'
        self.plan.is_active = True
        self.plan.save(update_fields=['stripe_price_id', 'is_active', 'updated_at'])

    @override_settings(PRACTITIONER_BILLING_ENABLED=False)
    def test_checkout_start_requires_billing_enabled(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:checkout_start'))

        self.assertRedirects(response, reverse('billing:overview'))
        self.assertFalse(ProfessionalSubscription.objects.filter(professional=self.profile).exists())

    @override_settings(PRACTITIONER_BILLING_ENABLED=True, STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.billing.payments.stripe.checkout.Session.create')
    def test_checkout_start_redirects_to_stripe(self, mock_checkout_create):
        mock_checkout_create.return_value = SimpleNamespace(
            id='cs_test_prof_123',
            url='https://checkout.stripe.com/c/pay/cs_test_prof_123',
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:checkout_start'))

        self.assertRedirects(response, 'https://checkout.stripe.com/c/pay/cs_test_prof_123', fetch_redirect_response=False)
        subscription = ProfessionalSubscription.objects.get(professional=self.profile)
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PENDING_LAUNCH)
        self.assertEqual(subscription.plan.code, 'founding-annual')

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_checkout_completion_activates_subscription(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.PENDING_LAUNCH,
        )
        mock_construct_event.return_value = {
            'type': 'checkout.session.completed',
            'data': {
                'object': {
                    'id': 'cs_bill_123',
                    'subscription': 'sub_123',
                    'customer': 'cus_123',
                    'metadata': {
                        'professional_profile_id': str(self.profile.pk),
                        'professional_subscription_id': str(subscription.pk),
                    },
                }
            },
        }

        response = self.client.post(
            reverse('billing:stripe_webhook'),
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig_test',
        )

        self.assertEqual(response.status_code, 200)
        subscription.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.ACTIVE)
        self.assertEqual(subscription.stripe_subscription_id, 'sub_123')
        self.assertEqual(subscription.stripe_customer_id, 'cus_123')
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.ACTIVE)
        self.assertEqual(self.profile.stripe_customer_id, 'cus_123')
