from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.catalog.models import Category, Service
from apps.professionals.models import ProfessionalProfile


CATEGORIES = [
    {
        'name': 'Wellness',
        'slug': 'wellness',
        'description': 'Body-centered wellness sessions and supportive care.',
    },
    {
        'name': 'Spirituality',
        'slug': 'spirituality',
        'description': 'Guidance and practices for spiritual alignment.',
    },
    {
        'name': 'Beauty',
        'slug': 'beauty',
        'description': 'Ritual-infused beauty and personal care services.',
    },
    {
        'name': 'Coaching',
        'slug': 'coaching',
        'description': 'Personal and professional transformation coaching.',
    },
]


PREVIEW_PROFILES = [
    {
        'username': 'preview_river_sage',
        'email': 'river.sage@example.com',
        'display_name': 'River Sage',
        'business_name': 'River Sage Wellness Studio',
        'headline': 'Somatic wellness and stress reset sessions',
        'bio': 'I help clients calm the nervous system through grounded somatic practices, breath pacing, and clear aftercare rituals.',
        'modalities': 'somatic coaching, breathwork, mindfulness',
        'location': 'Portland',
        'is_virtual': True,
        'years_experience': 8,
        'services': [
            {
                'category_slug': 'wellness',
                'name': 'Somatic Reset Session',
                'description': 'A practical body-based session for down-regulation and clarity.',
                'duration_minutes': 60,
                'price_cents': 12500,
                'delivery_format': Service.DeliveryFormat.BOTH,
                'is_active': True,
            },
            {
                'category_slug': 'wellness',
                'name': 'Breathwork Integration',
                'description': 'Breath sequence plus integration notes for home practice.',
                'duration_minutes': 45,
                'price_cents': 9800,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
                'is_active': True,
            },
        ],
    },
    {
        'username': 'preview_luna_ash',
        'email': 'luna.ash@example.com',
        'display_name': 'Luna Ash',
        'business_name': 'Luna Ash Spiritual Care',
        'headline': 'Intuitive mentorship and ritual planning',
        'bio': 'I support transition periods with intuitive sessions that combine practical reflection and ceremonial intention.',
        'modalities': 'intuitive guidance, ritual design, meditation',
        'location': 'Los Angeles',
        'is_virtual': True,
        'years_experience': 10,
        'services': [
            {
                'category_slug': 'spirituality',
                'name': 'Ritual Planning Consultation',
                'description': 'Design a personalized ritual for milestones and transitions.',
                'duration_minutes': 75,
                'price_cents': 16500,
                'delivery_format': Service.DeliveryFormat.BOTH,
                'is_active': True,
            },
        ],
    },
    {
        'username': 'preview_mina_sol',
        'email': 'mina.sol@example.com',
        'display_name': 'Mina Sol',
        'business_name': 'Mina Sol Beauty Rituals',
        'headline': 'Beauty rituals that center confidence and care',
        'bio': 'My approach blends skin support with confidence coaching so each appointment feels restorative, not rushed.',
        'modalities': 'holistic esthetics, beauty ritual, confidence support',
        'location': 'Austin',
        'is_virtual': False,
        'years_experience': 6,
        'services': [
            {
                'category_slug': 'beauty',
                'name': 'Glow Ritual Facial',
                'description': 'A skin-supportive ritual with consultation and aftercare plan.',
                'duration_minutes': 90,
                'price_cents': 18500,
                'delivery_format': Service.DeliveryFormat.IN_PERSON,
                'is_active': True,
            },
        ],
    },
    {
        'username': 'preview_noah_elm',
        'email': 'noah.elm@example.com',
        'display_name': 'Noah Elm',
        'business_name': 'Elm Path Coaching',
        'headline': 'Career and leadership coaching for transitions',
        'bio': 'I work with mission-driven founders and operators who need strategic momentum without burnout.',
        'modalities': 'career coaching, leadership, communication',
        'location': 'Seattle',
        'is_virtual': True,
        'years_experience': 12,
        'services': [
            {
                'category_slug': 'coaching',
                'name': 'Clarity Strategy Session',
                'description': 'Action-oriented coaching focused on high-stakes decisions.',
                'duration_minutes': 60,
                'price_cents': 22000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
                'is_active': True,
            },
            {
                'category_slug': 'coaching',
                'name': 'Monthly Leadership Intensive',
                'description': 'Four weekly sessions with accountability and tools.',
                'duration_minutes': 60,
                'price_cents': 78000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
                'is_active': True,
            },
        ],
    },
    {
        'username': 'preview_anya_reed',
        'email': 'anya.reed@example.com',
        'display_name': 'Anya Reed',
        'business_name': 'Reed Integrative Practice',
        'headline': 'Trauma-aware wellness and spiritual integration',
        'bio': 'Clients come for integrated sessions that bridge emotional grounding, spiritual discernment, and daily routines.',
        'modalities': 'trauma-aware wellness, meditation, integrative support',
        'location': 'Denver',
        'is_virtual': True,
        'years_experience': 9,
        'services': [
            {
                'category_slug': 'wellness',
                'name': 'Ground + Integrate Session',
                'description': 'Whole-person support session with practical follow-through.',
                'duration_minutes': 70,
                'price_cents': 14500,
                'delivery_format': Service.DeliveryFormat.BOTH,
                'is_active': True,
            },
            {
                'category_slug': 'spirituality',
                'name': 'Meditation Mentorship',
                'description': 'Build a sustainable meditation rhythm with guidance.',
                'duration_minutes': 50,
                'price_cents': 11000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
                'is_active': True,
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Seed curated preview data for discovery pages.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing preview profiles/services before seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['clear']:
            self._clear_preview_data()

        categories = self._upsert_categories()
        profile_count = 0
        service_count = 0

        for item in PREVIEW_PROFILES:
            user, _ = User.objects.update_or_create(
                username=item['username'],
                defaults={
                    'email': item['email'],
                    'display_name': item['display_name'],
                    'role': User.Role.PROFESSIONAL,
                    'is_active': True,
                },
            )
            if not user.has_usable_password():
                user.set_unusable_password()
                user.save(update_fields=['password'])

            profile, _ = ProfessionalProfile.objects.update_or_create(
                user=user,
                defaults={
                    'business_name': item['business_name'],
                    'headline': item['headline'],
                    'bio': item['bio'],
                    'modalities': item['modalities'],
                    'location': item['location'],
                    'is_virtual': item['is_virtual'],
                    'years_experience': item['years_experience'],
                    'approval_status': ProfessionalProfile.ApprovalStatus.APPROVED,
                    'is_visible': True,
                },
            )
            profile_count += 1

            for service_item in item['services']:
                category = categories[service_item['category_slug']]
                Service.objects.update_or_create(
                    professional=profile,
                    name=service_item['name'],
                    defaults={
                        'category': category,
                        'description': service_item['description'],
                        'duration_minutes': service_item['duration_minutes'],
                        'price_cents': service_item['price_cents'],
                        'delivery_format': service_item['delivery_format'],
                        'is_active': service_item['is_active'],
                    },
                )
                service_count += 1

        self.stdout.write(self.style.SUCCESS(f'Seeded {profile_count} preview profiles and {service_count} services.'))

    def _upsert_categories(self):
        categories = {}
        for item in CATEGORIES:
            category, _ = Category.objects.update_or_create(
                slug=item['slug'],
                defaults={
                    'name': item['name'],
                    'description': item['description'],
                },
            )
            categories[item['slug']] = category
        return categories

    def _clear_preview_data(self):
        usernames = [item['username'] for item in PREVIEW_PROFILES]
        users = User.objects.filter(username__in=usernames)
        Service.objects.filter(professional__user__in=users).delete()
        ProfessionalProfile.objects.filter(user__in=users).delete()
        users.delete()
