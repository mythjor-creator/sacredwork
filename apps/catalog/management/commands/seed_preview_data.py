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


MARKETING_PROFILE_BLUEPRINTS = [
    {
        'slug': 'alina-moss',
        'display_name': 'Alina Moss',
        'business_name': 'Moss Ritual Wellness',
        'headline': 'Nervous-system healing with practical rituals',
        'modalities': 'somatic coaching, breathwork, stress recovery',
        'location': 'Portland',
        'years_experience': 9,
        'category_slug': 'wellness',
        'service_name': 'Somatic Renewal Intensive',
        'service_description': 'A focused reset session with a practical aftercare plan.',
        'duration_minutes': 75,
        'price_cents': 16500,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'june-kai',
        'display_name': 'June Kai',
        'business_name': 'Kai Breath Studio',
        'headline': 'Breathwork for confidence and emotional release',
        'modalities': 'breathwork, mindfulness, emotional regulation',
        'location': 'San Diego',
        'years_experience': 7,
        'category_slug': 'wellness',
        'service_name': 'Breath + Reset Session',
        'service_description': 'Structured breathwork with guided integration.',
        'duration_minutes': 60,
        'price_cents': 12800,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'mira-lane',
        'display_name': 'Mira Lane',
        'business_name': 'Lane Integrative Wellness',
        'headline': 'Whole-person wellness for life transitions',
        'modalities': 'wellness planning, mindfulness, burnout recovery',
        'location': 'Denver',
        'years_experience': 11,
        'category_slug': 'wellness',
        'service_name': 'Transition Care Session',
        'service_description': 'Guided transition support with weekly routines.',
        'duration_minutes': 70,
        'price_cents': 15200,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'sami-vale',
        'display_name': 'Sami Vale',
        'business_name': 'Vale Body Wisdom',
        'headline': 'Embodied healing sessions for stress and fatigue',
        'modalities': 'somatic healing, grounding, body awareness',
        'location': 'Phoenix',
        'years_experience': 8,
        'category_slug': 'wellness',
        'service_name': 'Embodied Grounding Session',
        'service_description': 'Body-first support for emotional steadiness.',
        'duration_minutes': 50,
        'price_cents': 11800,
        'delivery_format': Service.DeliveryFormat.IN_PERSON,
        'is_virtual': False,
    },
    {
        'slug': 'nora-finch',
        'display_name': 'Nora Finch',
        'business_name': 'Finch Soul Guidance',
        'headline': 'Intuitive guidance rooted in practical clarity',
        'modalities': 'intuitive guidance, meditation, spiritual support',
        'location': 'Los Angeles',
        'years_experience': 12,
        'category_slug': 'spirituality',
        'service_name': 'Intuitive Clarity Session',
        'service_description': 'Discernment and direction for major decisions.',
        'duration_minutes': 60,
        'price_cents': 17000,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'isla-ember',
        'display_name': 'Isla Ember',
        'business_name': 'Ember Sacred Studio',
        'headline': 'Ceremony design for meaningful milestones',
        'modalities': 'ritual design, spiritual mentoring, ceremony',
        'location': 'Santa Fe',
        'years_experience': 10,
        'category_slug': 'spirituality',
        'service_name': 'Milestone Ritual Design',
        'service_description': 'Custom ceremony planning for transitions.',
        'duration_minutes': 90,
        'price_cents': 24000,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'kira-dawn',
        'display_name': 'Kira Dawn',
        'business_name': 'Dawn Spiritual Mentorship',
        'headline': 'Meditation mentorship for busy professionals',
        'modalities': 'meditation, spiritual rhythm, grounding',
        'location': 'Seattle',
        'years_experience': 6,
        'category_slug': 'spirituality',
        'service_name': 'Meditation Rhythm Coaching',
        'service_description': 'Create a repeatable daily spiritual practice.',
        'duration_minutes': 45,
        'price_cents': 9900,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'zara-pine',
        'display_name': 'Zara Pine',
        'business_name': 'Pine Moon Guidance',
        'headline': 'Compassionate intuitive support with structure',
        'modalities': 'spiritual coaching, journaling, intuitive reflection',
        'location': 'Chicago',
        'years_experience': 7,
        'category_slug': 'spirituality',
        'service_name': 'Aligned Reflection Session',
        'service_description': 'Clarify next steps through guided reflection.',
        'duration_minutes': 55,
        'price_cents': 11200,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'maya-quill',
        'display_name': 'Maya Quill',
        'business_name': 'Quill Beauty Rituals',
        'headline': 'Intentional beauty sessions for confidence',
        'modalities': 'beauty ritual, skin support, confidence care',
        'location': 'Austin',
        'years_experience': 5,
        'category_slug': 'beauty',
        'service_name': 'Confidence Glow Ritual',
        'service_description': 'Skin and self-image session with aftercare.',
        'duration_minutes': 80,
        'price_cents': 17800,
        'delivery_format': Service.DeliveryFormat.IN_PERSON,
        'is_virtual': False,
    },
    {
        'slug': 'tessa-rose',
        'display_name': 'Tessa Rose',
        'business_name': 'Rose Ritual Aesthetics',
        'headline': 'Holistic skin ritual and nervous-system calm',
        'modalities': 'holistic esthetics, beauty ritual, facial care',
        'location': 'Nashville',
        'years_experience': 9,
        'category_slug': 'beauty',
        'service_name': 'Holistic Skin Ritual',
        'service_description': 'Facial ritual with wellness-informed pacing.',
        'duration_minutes': 90,
        'price_cents': 19600,
        'delivery_format': Service.DeliveryFormat.IN_PERSON,
        'is_virtual': False,
    },
    {
        'slug': 'olive-rain',
        'display_name': 'Olive Rain',
        'business_name': 'Rain Beauty + Ritual',
        'headline': 'Beauty care that supports emotional reset',
        'modalities': 'beauty ritual, personal style support, skin care',
        'location': 'Miami',
        'years_experience': 6,
        'category_slug': 'beauty',
        'service_name': 'Ritual Beauty Reset',
        'service_description': 'Intentional beauty session with reflection.',
        'duration_minutes': 60,
        'price_cents': 14900,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'hannah-bloom',
        'display_name': 'Hannah Bloom',
        'business_name': 'Bloom Confidence Studio',
        'headline': 'Confidence rituals through beauty and coaching',
        'modalities': 'beauty confidence, image support, self-trust',
        'location': 'New York',
        'years_experience': 8,
        'category_slug': 'beauty',
        'service_name': 'Confidence Mirror Session',
        'service_description': 'Practical confidence support through beauty habits.',
        'duration_minutes': 75,
        'price_cents': 17200,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'cole-arden',
        'display_name': 'Cole Arden',
        'business_name': 'Arden Leadership Lab',
        'headline': 'Leadership coaching without burnout',
        'modalities': 'leadership coaching, communication, team clarity',
        'location': 'San Francisco',
        'years_experience': 13,
        'category_slug': 'coaching',
        'service_name': 'Leadership Clarity Intensive',
        'service_description': 'Strategic leadership coaching with actionable plans.',
        'duration_minutes': 60,
        'price_cents': 23500,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'ryan-kestrel',
        'display_name': 'Ryan Kestrel',
        'business_name': 'Kestrel Career Studio',
        'headline': 'Career strategy for pivots and promotions',
        'modalities': 'career coaching, strategy, interview readiness',
        'location': 'Boston',
        'years_experience': 11,
        'category_slug': 'coaching',
        'service_name': 'Career Pivot Session',
        'service_description': 'Navigate your next move with strategic clarity.',
        'duration_minutes': 60,
        'price_cents': 18500,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'elena-cove',
        'display_name': 'Elena Cove',
        'business_name': 'Cove Relationship Coaching',
        'headline': 'Relationship coaching for healthy communication',
        'modalities': 'relationship coaching, communication, boundaries',
        'location': 'Atlanta',
        'years_experience': 10,
        'category_slug': 'coaching',
        'service_name': 'Communication Reset Session',
        'service_description': 'Frameworks for aligned conversations and boundaries.',
        'duration_minutes': 70,
        'price_cents': 16800,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'omar-frost',
        'display_name': 'Omar Frost',
        'business_name': 'Frost Performance Coaching',
        'headline': 'Performance habits for founders and operators',
        'modalities': 'performance coaching, habits, accountability',
        'location': 'Dallas',
        'years_experience': 9,
        'category_slug': 'coaching',
        'service_name': 'Founder Momentum Session',
        'service_description': 'Drive measurable progress with sustainable systems.',
        'duration_minutes': 55,
        'price_cents': 15800,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
    {
        'slug': 'lena-skye',
        'display_name': 'Lena Skye',
        'business_name': 'Skye Healing Collective',
        'headline': 'Integrated healing for mind, body, and spirit',
        'modalities': 'integrative healing, mindfulness, spiritual coaching',
        'location': 'Boulder',
        'years_experience': 14,
        'category_slug': 'wellness',
        'service_name': 'Integrated Healing Session',
        'service_description': 'Combined wellness and spiritual support plan.',
        'duration_minutes': 80,
        'price_cents': 21000,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'piper-hale',
        'display_name': 'Piper Hale',
        'business_name': 'Hale Ritual Coaching',
        'headline': 'Coaching and ceremony for life transitions',
        'modalities': 'transition coaching, ritual, reflection',
        'location': 'Minneapolis',
        'years_experience': 8,
        'category_slug': 'spirituality',
        'service_name': 'Transition Ritual Coaching',
        'service_description': 'Bridge practical coaching with personal ceremony.',
        'duration_minutes': 75,
        'price_cents': 17600,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'jade-quartz',
        'display_name': 'Jade Quartz',
        'business_name': 'Quartz Beauty Therapy',
        'headline': 'Beauty support for confidence after burnout',
        'modalities': 'beauty recovery, confidence coaching, skin ritual',
        'location': 'Charlotte',
        'years_experience': 7,
        'category_slug': 'beauty',
        'service_name': 'Confidence Recovery Ritual',
        'service_description': 'Restore confidence through mindful care rituals.',
        'duration_minutes': 65,
        'price_cents': 15400,
        'delivery_format': Service.DeliveryFormat.BOTH,
        'is_virtual': True,
    },
    {
        'slug': 'evan-north',
        'display_name': 'Evan North',
        'business_name': 'North Path Coaching',
        'headline': 'Career and purpose alignment coaching',
        'modalities': 'career alignment, values coaching, planning',
        'location': 'Philadelphia',
        'years_experience': 10,
        'category_slug': 'coaching',
        'service_name': 'Purpose Alignment Strategy',
        'service_description': 'Clarify values and translate them to a work plan.',
        'duration_minutes': 60,
        'price_cents': 17200,
        'delivery_format': Service.DeliveryFormat.VIRTUAL,
        'is_virtual': True,
    },
]


def _marketing_profiles():
    profiles = []
    for item in MARKETING_PROFILE_BLUEPRINTS:
        slug = item['slug']
        profiles.append(
            {
                'username': f'marketing_{slug.replace('-', '_')}',
                'email': f'{slug}@example.com',
                'display_name': item['display_name'],
                'business_name': item['business_name'],
                'headline': item['headline'],
                'bio': (
                    f"{item['display_name']} supports clients through {item['modalities']}. "
                    'Sessions are designed to be practical, warm, and results-focused for real-world change.'
                ),
                'modalities': item['modalities'],
                'location': item['location'],
                'is_virtual': item['is_virtual'],
                'years_experience': item['years_experience'],
                'services': [
                    {
                        'category_slug': item['category_slug'],
                        'name': item['service_name'],
                        'description': item['service_description'],
                        'duration_minutes': item['duration_minutes'],
                        'price_cents': item['price_cents'],
                        'delivery_format': item['delivery_format'],
                        'is_active': True,
                    }
                ],
            }
        )
    return profiles


DATASETS = {
    'preview': PREVIEW_PROFILES,
    'marketing': _marketing_profiles(),
}


class Command(BaseCommand):
    help = 'Seed curated preview data for discovery pages.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Delete existing preview profiles/services before seeding.',
        )
        parser.add_argument(
            '--dataset',
            choices=sorted(DATASETS.keys()),
            default='preview',
            help='Choose which sample dataset to seed.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dataset_name = options['dataset']
        selected_profiles = DATASETS[dataset_name]

        if options['clear']:
            self._clear_preview_data(selected_profiles)

        categories = self._upsert_categories()
        profile_count = 0
        service_count = 0

        for item in selected_profiles:
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

        self.stdout.write(
            self.style.SUCCESS(
                f'Seeded {profile_count} {dataset_name} profiles and {service_count} services.'
            )
        )

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

    def _clear_preview_data(self, selected_profiles):
        usernames = [item['username'] for item in selected_profiles]
        users = User.objects.filter(username__in=usernames)
        Service.objects.filter(professional__user__in=users).delete()
        ProfessionalProfile.objects.filter(user__in=users).delete()
        users.delete()
