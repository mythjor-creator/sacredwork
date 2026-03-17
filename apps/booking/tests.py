from datetime import time, timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.professionals.models import ProfessionalProfile

from .models import AvailabilityWindow, Booking
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
