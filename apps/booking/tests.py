from datetime import time, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.core import mail
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.professionals.models import ProfessionalProfile

from .models import AvailabilityWindow, Booking, BookingPaymentIntent
from .services import create_booking, generate_service_slots, transition_booking


class BookingFlowTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Wellness', slug='wellness')
		self.professional_user = User.objects.create_user(
			username='booking-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Booking Studio',
			headline='Trauma-informed practitioner',
			bio='Grounded sessions for recovery and support.',
			modalities='somatic coaching',
			location='Austin',
			is_virtual=True,
			years_experience=5,
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Somatic Session',
			description='One-on-one guided support.',
			duration_minutes=60,
			price_cents=14000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)
		self.client_user = User.objects.create_user(
			username='booking-client',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)

	def _add_future_window(self):
		target_date = timezone.localdate() + timedelta(days=1)
		AvailabilityWindow.objects.create(
			professional=self.profile,
			weekday=target_date.isoweekday(),
			start_time=time(hour=9, minute=0),
			end_time=time(hour=12, minute=0),
		)
		return target_date

	def test_professional_can_add_availability_window(self):
		self.client.force_login(self.professional_user)
		response = self.client.post(
			reverse('booking:availability'),
			{
				'weekday': AvailabilityWindow.Weekday.MONDAY,
				'start_time': '09:00',
				'end_time': '13:00',
				'is_active': True,
			},
		)

		self.assertRedirects(response, reverse('booking:availability'))
		self.assertEqual(self.profile.availability_windows.count(), 1)

	def test_client_can_book_available_slot(self):
		target_date = self._add_future_window()
		self.client.force_login(self.client_user)

		slots = generate_service_slots(self.service, from_date=target_date)
		response = self.client.post(
			reverse('booking:create', args=[self.service.pk]),
			{
				'slot': slots[0]['start_at'].isoformat(),
				'intake_notes': 'Looking for support with stress.',
			},
		)

		self.assertRedirects(response, reverse('booking:list'))
		booking = Booking.objects.get(client=self.client_user)
		self.assertEqual(booking.service, self.service)
		self.assertEqual(booking.price_cents_snapshot, self.service.price_cents)

	def test_overlapping_booking_is_rejected(self):
		target_date = self._add_future_window()
		first_slot = generate_service_slots(self.service, from_date=target_date)[0]['start_at']
		create_booking(self.client_user, self.service, first_slot)

		second_client = User.objects.create_user(
			username='second-client',
			password='StrongPass123!!',
			role=User.Role.CLIENT,
		)

		with self.assertRaisesMessage(ValueError, 'That time is no longer available.'):
			create_booking(second_client, self.service, first_slot)

	def test_professional_can_confirm_and_complete_booking(self):
		target_date = self._add_future_window()
		start_at = generate_service_slots(self.service, from_date=target_date)[0]['start_at']
		booking = create_booking(self.client_user, self.service, start_at)

		self.client.force_login(self.professional_user)
		confirm_response = self.client.post(reverse('booking:action', args=[booking.pk, 'confirm']))
		self.assertRedirects(confirm_response, reverse('booking:list'))
		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.CONFIRMED)

		complete_response = self.client.post(reverse('booking:action', args=[booking.pk, 'complete']))
		self.assertRedirects(complete_response, reverse('booking:list'))
		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.COMPLETED)

	def test_client_can_cancel_confirmed_booking(self):
		target_date = self._add_future_window()
		start_at = generate_service_slots(self.service, from_date=target_date)[0]['start_at']
		booking = create_booking(self.client_user, self.service, start_at)
		transition_booking(booking, self.professional_user, Booking.Status.CONFIRMED)

		self.client.force_login(self.client_user)
		response = self.client.post(reverse('booking:action', args=[booking.pk, 'cancel']))
		self.assertRedirects(response, reverse('booking:list'))
		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.CANCELLED)

	def test_client_cannot_confirm_booking(self):
		target_date = self._add_future_window()
		start_at = generate_service_slots(self.service, from_date=target_date)[0]['start_at']
		booking = create_booking(self.client_user, self.service, start_at)

		self.client.force_login(self.client_user)
		response = self.client.post(reverse('booking:action', args=[booking.pk, 'confirm']))
		self.assertRedirects(response, reverse('booking:list'))
		booking.refresh_from_db()
		self.assertEqual(booking.status, Booking.Status.REQUESTED)


class BookingEmailTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Email Wellness', slug='email-wellness')
		self.professional_user = User.objects.create_user(
			username='email-pro',
			password='StrongPass123!!',
			email='pro@example.com',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Email Studio',
			headline='Email test practitioner',
			bio='Testing email notifications.',
			modalities='reiki',
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Email Session',
			description='Session for email tests.',
			duration_minutes=60,
			price_cents=10000,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)
		self.client_user = User.objects.create_user(
			username='email-client',
			password='StrongPass123!!',
			email='client@example.com',
			role=User.Role.CLIENT,
		)
		target_date = timezone.localdate() + timedelta(days=1)
		AvailabilityWindow.objects.create(
			professional=self.profile,
			weekday=target_date.isoweekday(),
			start_time=time(hour=10, minute=0),
			end_time=time(hour=12, minute=0),
		)
		self.target_date = target_date

	def _make_booking(self):
		start_at = generate_service_slots(self.service, from_date=self.target_date)[0]['start_at']
		mail.outbox.clear()
		return create_booking(self.client_user, self.service, start_at)

	def test_booking_requested_sends_two_emails(self):
		booking = self._make_booking()
		self.assertEqual(len(mail.outbox), 2)
		recipients = {msg.to[0] for msg in mail.outbox}
		self.assertIn('client@example.com', recipients)
		self.assertIn('pro@example.com', recipients)
		subjects = [msg.subject for msg in mail.outbox]
		self.assertTrue(any('request sent' in s for s in subjects))
		self.assertTrue(any('New booking request' in s for s in subjects))

	def test_booking_confirmed_sends_email_to_client(self):
		booking = self._make_booking()
		mail.outbox.clear()
		transition_booking(booking, self.professional_user, Booking.Status.CONFIRMED)
		self.assertEqual(len(mail.outbox), 1)
		self.assertIn('client@example.com', mail.outbox[0].to)
		self.assertIn('confirmed', mail.outbox[0].subject.lower())

	def test_booking_cancelled_sends_two_emails(self):
		booking = self._make_booking()
		transition_booking(booking, self.professional_user, Booking.Status.CONFIRMED)
		mail.outbox.clear()
		transition_booking(booking, self.client_user, Booking.Status.CANCELLED)
		self.assertEqual(len(mail.outbox), 2)
		recipients = {msg.to[0] for msg in mail.outbox}
		self.assertIn('client@example.com', recipients)
		self.assertIn('pro@example.com', recipients)

	def test_no_email_sent_on_complete(self):
		booking = self._make_booking()
		transition_booking(booking, self.professional_user, Booking.Status.CONFIRMED)
		mail.outbox.clear()
		transition_booking(booking, self.professional_user, Booking.Status.COMPLETED)
		self.assertEqual(len(mail.outbox), 0)


class BookingPaymentTests(TestCase):
	def setUp(self):
		self.category = Category.objects.create(name='Payment Wellness', slug='payment-wellness')
		self.professional_user = User.objects.create_user(
			username='payment-pro',
			password='StrongPass123!!',
			email='payment-pro@example.com',
			role=User.Role.PROFESSIONAL,
		)
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Payment Studio',
			headline='Payment-enabled practitioner',
			bio='Testing Stripe checkout.',
			modalities='coaching',
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Payment Session',
			description='Session for payment tests.',
			duration_minutes=60,
			price_cents=8500,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)
		self.client_user = User.objects.create_user(
			username='payment-client',
			password='StrongPass123!!',
			email='payment-client@example.com',
			role=User.Role.CLIENT,
		)
		target_date = timezone.localdate() + timedelta(days=1)
		AvailabilityWindow.objects.create(
			professional=self.profile,
			weekday=target_date.isoweekday(),
			start_time=time(hour=10, minute=0),
			end_time=time(hour=12, minute=0),
		)
		self.start_at = generate_service_slots(self.service, from_date=target_date)[0]['start_at']

	@override_settings(STRIPE_SECRET_KEY='sk_test_123')
	@patch('apps.booking.payments.stripe.checkout.Session.create')
	def test_booking_create_redirects_to_stripe_checkout(self, mock_checkout_create):
		mock_checkout_create.return_value = SimpleNamespace(
			id='cs_test_123',
			url='https://checkout.stripe.com/c/pay/cs_test_123',
		)

		self.client.force_login(self.client_user)
		response = self.client.post(
			reverse('booking:create', args=[self.service.pk]),
			{
				'slot': self.start_at.isoformat(),
				'intake_notes': 'Need support with transitions.',
			},
		)

		self.assertRedirects(response, 'https://checkout.stripe.com/c/pay/cs_test_123', fetch_redirect_response=False)
		intent = BookingPaymentIntent.objects.get(client=self.client_user)
		self.assertEqual(intent.status, BookingPaymentIntent.Status.PENDING)
		self.assertEqual(intent.stripe_checkout_session_id, 'cs_test_123')
		self.assertEqual(Booking.objects.count(), 0)

	@override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test_123')
	@patch('apps.booking.payments.stripe.Webhook.construct_event')
	def test_webhook_completion_creates_booking(self, mock_construct_event):
		intent = BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=self.start_at,
			intake_notes='Webhook flow',
			stripe_checkout_session_id='cs_test_456',
		)
		mock_construct_event.return_value = {
			'type': 'checkout.session.completed',
			'data': {
				'object': {
					'id': 'cs_test_456',
					'payment_intent': 'pi_test_456',
					'metadata': {'booking_payment_intent_id': str(intent.pk)},
				}
			},
		}

		response = self.client.post(
			reverse('booking:stripe_webhook'),
			data='{}',
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='sig_test',
		)

		self.assertEqual(response.status_code, 200)
		intent.refresh_from_db()
		self.assertEqual(intent.status, BookingPaymentIntent.Status.COMPLETED)
		self.assertEqual(intent.stripe_payment_intent_id, 'pi_test_456')
		self.assertFalse(intent.requires_manual_refund)
		self.assertIsNotNone(intent.booking)

	@override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test_123')
	@patch('apps.booking.payments.stripe.Webhook.construct_event')
	def test_webhook_completion_sends_payment_received_email(self, mock_construct_event):
		intent = BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=self.start_at,
			intake_notes='Email test',
			stripe_checkout_session_id='cs_test_email',
		)
		mock_construct_event.return_value = {
			'type': 'checkout.session.completed',
			'data': {
				'object': {
					'id': 'cs_test_email',
					'payment_intent': 'pi_test_email',
					'metadata': {'booking_payment_intent_id': str(intent.pk)},
				}
			},
		}

		mail.outbox.clear()
		self.client.post(
			reverse('booking:stripe_webhook'),
			data='{}',
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='sig_test',
		)

		self.assertEqual(len(mail.outbox), 2)
		recipients = {msg.to[0] for msg in mail.outbox}
		self.assertIn('payment-client@example.com', recipients)
		self.assertIn(self.professional_user.email, recipients)
		subjects = [msg.subject for msg in mail.outbox]
		self.assertTrue(any('payment received' in s.lower() for s in subjects))
		self.assertTrue(any('paid booking' in s.lower() for s in subjects))

	@override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test_123')
	@patch('apps.booking.payments.stripe.Webhook.construct_event')
	def test_webhook_slot_collision_sends_no_email(self, mock_construct_event):
		_ = create_booking(self.client_user, self.service, self.start_at)
		intent = BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=self.start_at,
			intake_notes='Collision no-email test',
			stripe_checkout_session_id='cs_test_collision_email',
		)
		mock_construct_event.return_value = {
			'type': 'checkout.session.completed',
			'data': {
				'object': {
					'id': 'cs_test_collision_email',
					'payment_intent': 'pi_test_collision_email',
					'metadata': {'booking_payment_intent_id': str(intent.pk)},
				}
			},
		}

		mail.outbox.clear()
		self.client.post(
			reverse('booking:stripe_webhook'),
			data='{}',
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='sig_test',
		)

		self.assertEqual(len(mail.outbox), 0)

	@override_settings(STRIPE_SECRET_KEY='sk_test_123', STRIPE_WEBHOOK_SECRET='whsec_test_123')
	@patch('apps.booking.payments.stripe.Webhook.construct_event')
	def test_webhook_marks_manual_refund_when_slot_taken_after_payment(self, mock_construct_event):
		_ = create_booking(self.client_user, self.service, self.start_at)
		intent = BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=self.start_at,
			intake_notes='Competing paid checkout',
			stripe_checkout_session_id='cs_test_conflict',
		)
		mock_construct_event.return_value = {
			'type': 'checkout.session.completed',
			'data': {
				'object': {
					'id': 'cs_test_conflict',
					'payment_intent': 'pi_test_conflict',
					'metadata': {'booking_payment_intent_id': str(intent.pk)},
				}
			},
		}

		response = self.client.post(
			reverse('booking:stripe_webhook'),
			data='{}',
			content_type='application/json',
			HTTP_STRIPE_SIGNATURE='sig_test',
		)

		self.assertEqual(response.status_code, 200)
		intent.refresh_from_db()
		self.assertEqual(intent.status, BookingPaymentIntent.Status.FAILED)
		self.assertTrue(intent.requires_manual_refund)
		self.assertIn('Slot became unavailable', intent.failure_reason)
		self.assertIsNone(intent.booking)

	@override_settings(STRIPE_SECRET_KEY='sk_test_123')
	@patch('apps.booking.payments.stripe.checkout.Session.create')
	def test_client_can_retry_failed_payment_intent(self, mock_checkout_create):
		intent = BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=self.start_at,
			intake_notes='Retry booking',
			status=BookingPaymentIntent.Status.FAILED,
			failure_reason='Temporary checkout issue',
		)
		mock_checkout_create.return_value = SimpleNamespace(
			id='cs_test_retry',
			url='https://checkout.stripe.com/c/pay/cs_test_retry',
		)

		self.client.force_login(self.client_user)
		response = self.client.post(reverse('booking:payment_retry', args=[intent.pk]))

		self.assertRedirects(response, 'https://checkout.stripe.com/c/pay/cs_test_retry', fetch_redirect_response=False)
		intent.refresh_from_db()
		self.assertEqual(intent.status, BookingPaymentIntent.Status.PENDING)
		self.assertEqual(intent.stripe_checkout_session_id, 'cs_test_retry')
		self.assertEqual(intent.failure_reason, '')
		self.assertFalse(intent.requires_manual_refund)


class RefundResolutionAdminTests(TestCase):
	def setUp(self):
		self.admin_user = User.objects.create_superuser(
			username='refund-admin',
			password='StrongPass123!!',
			email='admin@example.com',
		)
		self.category = Category.objects.create(name='Refund Wellness', slug='refund-wellness')
		self.professional_user = User.objects.create_user(
			username='refund-pro',
			password='StrongPass123!!',
			role=User.Role.PROFESSIONAL,
		)
		from apps.professionals.models import ProfessionalProfile
		self.profile = ProfessionalProfile.objects.create(
			user=self.professional_user,
			business_name='Refund Studio',
			headline='Refund practitioner',
			bio='For refund testing.',
			modalities='reiki',
			approval_status=ProfessionalProfile.ApprovalStatus.APPROVED,
			is_visible=True,
		)
		self.client_user = User.objects.create_user(
			username='refund-client',
			password='StrongPass123!!',
			email='refund-client@example.com',
			role=User.Role.CLIENT,
		)
		self.service = Service.objects.create(
			professional=self.profile,
			category=self.category,
			name='Refund Session',
			description='Session that needs a refund.',
			duration_minutes=60,
			price_cents=9900,
			delivery_format=Service.DeliveryFormat.VIRTUAL,
		)

	def _make_failed_intent(self, **kwargs):
		return BookingPaymentIntent.objects.create(
			client=self.client_user,
			service=self.service,
			start_at=timezone.now() + timedelta(days=2),
			stripe_payment_intent_id='pi_refund_test',
			status=BookingPaymentIntent.Status.FAILED,
			requires_manual_refund=True,
			failure_reason='Slot became unavailable after successful payment.',
			**kwargs,
		)

	def test_mark_refund_resolved_action_clears_flag_and_sets_timestamp(self):
		intent = self._make_failed_intent(refund_id='re_test_abc')
		self.client.force_login(self.admin_user)

		response = self.client.post(
			reverse('admin:booking_bookingpaymentintent_changelist'),
			{
				'action': 'mark_refund_resolved',
				'_selected_action': [str(intent.pk)],
			},
		)

		self.assertEqual(response.status_code, 302)
		intent.refresh_from_db()
		self.assertFalse(intent.requires_manual_refund)
		self.assertIsNotNone(intent.refund_resolved_at)

	def test_action_warns_when_refund_id_is_missing(self):
		intent = self._make_failed_intent()  # no refund_id
		self.client.force_login(self.admin_user)

		response = self.client.post(
			reverse('admin:booking_bookingpaymentintent_changelist'),
			{
				'action': 'mark_refund_resolved',
				'_selected_action': [str(intent.pk)],
			},
			follow=True,
		)

		messages_text = [str(m) for m in response.context['messages']]
		self.assertTrue(any('no Stripe refund ID' in m for m in messages_text))
		# Record is still resolved (action resolves even with missing ID)
		intent.refresh_from_db()
		self.assertFalse(intent.requires_manual_refund)
		self.assertIsNotNone(intent.refund_resolved_at)

	def test_action_skips_already_resolved_records(self):
		intent = self._make_failed_intent(refund_id='re_already_done')
		intent.requires_manual_refund = False
		intent.refund_resolved_at = timezone.now()
		intent.save()

		self.client.force_login(self.admin_user)
		response = self.client.post(
			reverse('admin:booking_bookingpaymentintent_changelist'),
			{
				'action': 'mark_refund_resolved',
				'_selected_action': [str(intent.pk)],
			},
			follow=True,
		)

		messages_text = [str(m) for m in response.context['messages']]
		self.assertTrue(any('already had no pending refund' in m for m in messages_text))

	def test_refund_id_is_editable_on_detail_view(self):
		intent = self._make_failed_intent()
		self.client.force_login(self.admin_user)

		response = self.client.post(
			reverse('admin:booking_bookingpaymentintent_change', args=[intent.pk]),
			{
				'client': self.client_user.pk,
				'service': self.service.pk,
				'booking': '',
				'status': BookingPaymentIntent.Status.FAILED,
				'start_at_0': (timezone.now() + timedelta(days=2)).strftime('%Y-%m-%d'),
				'start_at_1': '10:00:00',
				'intake_notes': '',
				'failure_reason': 'Slot became unavailable after successful payment.',
				'requires_manual_refund': True,
				'refund_id': 're_entered_by_ops',
			},
		)

		self.assertIn(response.status_code, [200, 302])
		intent.refresh_from_db()
		self.assertEqual(intent.refund_id, 're_entered_by_ops')
