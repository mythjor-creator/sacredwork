from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile
from apps.waitlist.models import PractitionerWaitlistProfile

from .models import BillingWebhookEvent, ProfessionalSubscription, SubscriptionInvoice, SubscriptionPlan
from .payments import sync_subscription_from_stripe


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
        self.assertContains(response, 'Basic Practitioner Monthly')
        self.assertContains(response, 'Featured Practitioner Monthly')
        self.assertContains(response, 'Founding Practitioner Annual')


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
        self.basic_plan = SubscriptionPlan.objects.get(code='basic-monthly')
        self.featured_plan = SubscriptionPlan.objects.get(code='featured-monthly')
        self.founding_plan = SubscriptionPlan.objects.get(code='founding-annual')
        self.basic_plan.stripe_price_id = 'price_basic_123'
        self.featured_plan.stripe_price_id = 'price_featured_123'
        self.founding_plan.stripe_price_id = 'price_founding_123'
        self.basic_plan.is_active = True
        self.featured_plan.is_active = True
        self.founding_plan.is_active = True
        self.basic_plan.save(update_fields=['stripe_price_id', 'is_active', 'updated_at'])
        self.featured_plan.save(update_fields=['stripe_price_id', 'is_active', 'updated_at'])
        self.founding_plan.save(update_fields=['stripe_price_id', 'is_active', 'updated_at'])

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

        response = self.client.post(reverse('billing:checkout_start'), {'plan_code': 'basic-monthly'})

        self.assertRedirects(response, 'https://checkout.stripe.com/c/pay/cs_test_prof_123', fetch_redirect_response=False)
        subscription = ProfessionalSubscription.objects.get(professional=self.profile)
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PENDING_LAUNCH)
        self.assertEqual(subscription.plan.code, 'basic-monthly')
        self.assertFalse(subscription.founding_member_rate_locked)
        self.assertEqual(mock_checkout_create.call_args.kwargs['line_items'], [{'price': 'price_basic_123', 'quantity': 1}])
        self.assertEqual(mock_checkout_create.call_args.kwargs['subscription_data'], {'trial_period_days': 60})

    @override_settings(PRACTITIONER_BILLING_ENABLED=True, STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.billing.payments.stripe.checkout.Session.create')
    def test_checkout_start_defaults_from_waitlist_signup_tier(self, mock_checkout_create):
        mock_checkout_create.return_value = SimpleNamespace(
            id='cs_test_prof_456',
            url='https://checkout.stripe.com/c/pay/cs_test_prof_456',
        )
        PractitionerWaitlistProfile.objects.create(
            full_name='Checkout Pro',
            email=self.user.email,
            headline='Featured practitioner',
            modalities='coaching',
            practice_type=PractitionerWaitlistProfile.PracticeType.COACHING,
            signup_tier=PractitionerWaitlistProfile.SignupTier.FEATURED,
        )
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:checkout_start'))

        self.assertRedirects(response, 'https://checkout.stripe.com/c/pay/cs_test_prof_456', fetch_redirect_response=False)
        subscription = ProfessionalSubscription.objects.get(professional=self.profile)
        self.assertEqual(subscription.plan.code, 'featured-monthly')
        self.assertEqual(mock_checkout_create.call_args.kwargs['line_items'], [{'price': 'price_featured_123', 'quantity': 1}])
        self.assertEqual(mock_checkout_create.call_args.kwargs['subscription_data'], {'trial_period_days': 60})

    @override_settings(PRACTITIONER_BILLING_ENABLED=True, STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.billing.payments.stripe.billing_portal.Session.create')
    def test_portal_start_redirects_to_stripe_billing_portal(self, mock_portal_create):
        mock_portal_create.return_value = SimpleNamespace(
            id='bps_test_123',
            url='https://billing.stripe.com/p/session/test_123',
        )
        ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=self.founding_plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_customer_id='cus_portal_123',
            stripe_subscription_id='sub_portal_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        self.profile.stripe_customer_id = 'cus_portal_123'
        self.profile.save(update_fields=['subscription_status', 'stripe_customer_id', 'updated_at'])
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:portal_start'))

        self.assertRedirects(response, 'https://billing.stripe.com/p/session/test_123', fetch_redirect_response=False)

    @override_settings(PRACTITIONER_BILLING_ENABLED=True, STRIPE_SECRET_KEY='sk_test_123')
    def test_portal_start_requires_stripe_customer(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse('billing:portal_start'))

        self.assertRedirects(response, reverse('billing:overview'))

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

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_invoice_paid_records_invoice_and_activates(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.PAST_DUE,
            stripe_subscription_id='sub_inv_paid_123',
            stripe_customer_id='cus_inv_paid_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.PAST_DUE
        self.profile.subscription_fails_count = 2
        self.profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])

        mock_construct_event.return_value = {
            'type': 'invoice.paid',
            'data': {
                'object': {
                    'id': 'in_paid_test_123',
                    'subscription': 'sub_inv_paid_123',
                    'customer': 'cus_inv_paid_123',
                    'status': 'paid',
                    'amount_due': 7900,
                    'amount_paid': 7900,
                    'currency': 'usd',
                    'hosted_invoice_url': 'https://invoice.stripe.com/i/in_paid_test_123',
                    'status_transitions': {'paid_at': 1700000000},
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
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.ACTIVE)
        self.assertEqual(self.profile.subscription_fails_count, 0)
        from apps.billing.models import SubscriptionInvoice
        invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_paid_test_123')
        self.assertEqual(invoice.status, SubscriptionInvoice.Status.PAID)
        self.assertEqual(invoice.amount_due_cents, 7900)
        self.assertEqual(invoice.amount_paid_cents, 7900)
        self.assertIsNotNone(invoice.paid_at)

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_invoice_payment_failed_marks_past_due(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_inv_fail_123',
            stripe_customer_id='cus_inv_fail_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        self.profile.subscription_fails_count = 0
        self.profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])

        mock_construct_event.return_value = {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_fail_test_123',
                    'subscription': 'sub_inv_fail_123',
                    'customer': 'cus_inv_fail_123',
                    'status': 'open',
                    'amount_due': 7900,
                    'amount_paid': 0,
                    'currency': 'usd',
                    'hosted_invoice_url': 'https://invoice.stripe.com/i/in_fail_test_123',
                    'status_transitions': {'paid_at': None},
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
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PAST_DUE)
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.PAST_DUE)
        self.assertEqual(self.profile.subscription_fails_count, 1)
        invoice = SubscriptionInvoice.objects.get(stripe_invoice_id='in_fail_test_123')
        self.assertEqual(invoice.status, SubscriptionInvoice.Status.OPEN)
        self.assertEqual(invoice.amount_due_cents, 7900)
        self.assertEqual(invoice.amount_paid_cents, 0)
        self.assertIsNone(invoice.paid_at)

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_duplicate_invoice_payment_failed_is_idempotent(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_inv_dup_fail_123',
            stripe_customer_id='cus_inv_dup_fail_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        self.profile.subscription_fails_count = 0
        self.profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])

        mock_construct_event.return_value = {
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_fail_dup_test_123',
                    'subscription': 'sub_inv_dup_fail_123',
                    'customer': 'cus_inv_dup_fail_123',
                    'status': 'open',
                    'amount_due': 7900,
                    'amount_paid': 0,
                    'currency': 'usd',
                    'hosted_invoice_url': 'https://invoice.stripe.com/i/in_fail_dup_test_123',
                    'status_transitions': {'paid_at': None},
                }
            },
        }

        for _ in range(2):
            response = self.client.post(
                reverse('billing:stripe_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig_test',
            )
            self.assertEqual(response.status_code, 200)

        subscription.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PAST_DUE)
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.PAST_DUE)
        self.assertEqual(self.profile.subscription_fails_count, 1)
        self.assertEqual(SubscriptionInvoice.objects.filter(stripe_invoice_id='in_fail_dup_test_123').count(), 1)

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_duplicate_subscription_updated_past_due_is_idempotent(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_upd_dup_123',
            stripe_customer_id='cus_upd_dup_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        self.profile.subscription_fails_count = 0
        self.profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])

        mock_construct_event.return_value = {
            'type': 'customer.subscription.updated',
            'data': {
                'object': {
                    'id': 'sub_upd_dup_123',
                    'status': 'past_due',
                    'current_period_end': 1700000000,
                    'cancel_at_period_end': False,
                }
            },
        }

        for _ in range(2):
            response = self.client.post(
                reverse('billing:stripe_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig_test',
            )
            self.assertEqual(response.status_code, 200)

        subscription.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PAST_DUE)
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.PAST_DUE)
        self.assertEqual(self.profile.subscription_fails_count, 1)

    @override_settings(
        PRACTITIONER_BILLING_ENABLED=True,
        STRIPE_SECRET_KEY='sk_test_123',
        STRIPE_BILLING_WEBHOOK_SECRET='whsec_bill_test',
    )
    @patch('apps.billing.payments.stripe.Webhook.construct_event')
    def test_webhook_duplicate_event_id_is_processed_once(self, mock_construct_event):
        seeded_plan = SubscriptionPlan.objects.get(code='founding-annual')
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=seeded_plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_evt_once_123',
            stripe_customer_id='cus_evt_once_123',
        )
        self.profile.subscription_status = ProfessionalProfile.SubscriptionStatus.ACTIVE
        self.profile.subscription_fails_count = 0
        self.profile.save(update_fields=['subscription_status', 'subscription_fails_count', 'updated_at'])

        mock_construct_event.return_value = {
            'id': 'evt_billing_once_123',
            'type': 'invoice.payment_failed',
            'data': {
                'object': {
                    'id': 'in_evt_once_123',
                    'subscription': 'sub_evt_once_123',
                    'status': 'open',
                    'amount_due': 7900,
                    'amount_paid': 0,
                    'currency': 'usd',
                    'hosted_invoice_url': 'https://invoice.stripe.com/i/in_evt_once_123',
                    'status_transitions': {'paid_at': None},
                }
            },
        }

        for _ in range(2):
            response = self.client.post(
                reverse('billing:stripe_webhook'),
                data='{}',
                content_type='application/json',
                HTTP_STRIPE_SIGNATURE='sig_test',
            )
            self.assertEqual(response.status_code, 200)

        subscription.refresh_from_db()
        self.profile.refresh_from_db()
        webhook_event = BillingWebhookEvent.objects.get(stripe_event_id='evt_billing_once_123')
        self.assertEqual(subscription.status, ProfessionalSubscription.Status.PAST_DUE)
        self.assertEqual(self.profile.subscription_fails_count, 1)
        self.assertEqual(webhook_event.attempt_count, 1)
        self.assertIsNotNone(webhook_event.processed_at)


class BillingSyncTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(
            username='sync-pro',
            password='StrongPass123!!',
            email='sync-pro@example.com',
            role=User.Role.PROFESSIONAL,
        )
        self.profile = ProfessionalProfile.objects.create(
            user=user,
            business_name='Sync Studio',
            headline='Sync profile',
            bio='Profile used for Stripe sync tests.',
            modalities='coaching',
            subscription_status=ProfessionalProfile.SubscriptionStatus.ACTIVE,
        )
        self.plan = SubscriptionPlan.objects.get(code='founding-annual')
        self.subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=self.plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_sync_123',
            stripe_customer_id='cus_sync_old',
        )

    @override_settings(STRIPE_SECRET_KEY='sk_test_123')
    @patch('apps.billing.payments.stripe.Subscription.retrieve')
    def test_sync_subscription_from_stripe_updates_local_records(self, mock_retrieve):
        mock_retrieve.return_value = {
            'id': 'sub_sync_123',
            'status': 'past_due',
            'current_period_end': 1700000000,
            'cancel_at_period_end': True,
            'customer': 'cus_sync_new',
        }

        result = sync_subscription_from_stripe(self.subscription)

        self.assertTrue(result)
        self.subscription.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.subscription.status, ProfessionalSubscription.Status.PAST_DUE)
        self.assertEqual(self.subscription.stripe_customer_id, 'cus_sync_new')
        self.assertTrue(self.subscription.cancel_at_period_end)
        self.assertIsNotNone(self.subscription.current_period_end)
        self.assertEqual(self.profile.subscription_status, ProfessionalProfile.SubscriptionStatus.PAST_DUE)
        self.assertEqual(self.profile.stripe_customer_id, 'cus_sync_new')


class BillingAdminTests(TestCase):
    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            username='billing-admin',
            password='AdminPass123!!',
        )
        pro_user = User.objects.create_user(
            username='billing-admin-pro',
            password='StrongPass123!!',
            role=User.Role.PROFESSIONAL,
        )
        self.profile = ProfessionalProfile.objects.create(
            user=pro_user,
            business_name='Admin Billing Studio',
            headline='Admin billing profile',
            bio='Used for billing admin action tests.',
            modalities='coaching',
            subscription_status=ProfessionalProfile.SubscriptionStatus.ACTIVE,
        )
        self.plan = SubscriptionPlan.objects.get(code='founding-annual')

    @patch('apps.billing.admin.sync_subscription_from_stripe')
    def test_admin_sync_now_skips_records_without_stripe_subscription_id(self, mock_sync):
        with_stripe_id = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=self.plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_admin_sync_123',
        )
        other_user = User.objects.create_user(
            username='billing-admin-pro-2',
            password='StrongPass123!!',
            role=User.Role.PROFESSIONAL,
        )
        other_profile = ProfessionalProfile.objects.create(
            user=other_user,
            business_name='Admin Billing Studio 2',
            headline='Admin billing profile 2',
            bio='Second profile for admin action tests.',
            modalities='reiki',
            subscription_status=ProfessionalProfile.SubscriptionStatus.PRELAUNCH,
        )
        without_stripe_id = ProfessionalSubscription.objects.create(
            professional=other_profile,
            plan=self.plan,
            status=ProfessionalSubscription.Status.PENDING_LAUNCH,
            stripe_subscription_id='',
        )
        mock_sync.return_value = True

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('admin:billing_professionalsubscription_changelist'),
            {
                'action': 'sync_now',
                '_selected_action': [with_stripe_id.pk, without_stripe_id.pk],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_called_once_with(with_stripe_id)
        messages = [str(item) for item in response.context['messages']]
        self.assertTrue(any('1 synced, 1 skipped, 0 failed' in item for item in messages))

    @patch('apps.billing.admin.sync_subscription_from_stripe')
    def test_admin_sync_now_reports_failures(self, mock_sync):
        subscription = ProfessionalSubscription.objects.create(
            professional=self.profile,
            plan=self.plan,
            status=ProfessionalSubscription.Status.ACTIVE,
            stripe_subscription_id='sub_admin_sync_fail_123',
        )
        mock_sync.side_effect = RuntimeError('Stripe error')

        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse('admin:billing_professionalsubscription_changelist'),
            {
                'action': 'sync_now',
                '_selected_action': [subscription.pk],
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        mock_sync.assert_called_once_with(subscription)
        messages = [str(item) for item in response.context['messages']]
        self.assertTrue(any('0 synced, 0 skipped, 1 failed' in item for item in messages))


class BillingWebhookViewTests(TestCase):
    @patch('apps.billing.views.process_billing_webhook')
    def test_webhook_returns_bad_request_on_invalid_signature(self, mock_process_webhook):
        mock_process_webhook.side_effect = ValueError('Invalid webhook')

        response = self.client.post(
            reverse('billing:stripe_webhook'),
            data='{}',
            content_type='application/json',
            HTTP_STRIPE_SIGNATURE='sig_invalid',
        )

        self.assertEqual(response.status_code, 400)

    def test_webhook_rejects_get(self):
        response = self.client.get(reverse('billing:stripe_webhook'))

        self.assertEqual(response.status_code, 405)
