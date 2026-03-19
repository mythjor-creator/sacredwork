#!/usr/bin/env python
"""
Seed realistic development practitioner accounts and services.
Usage: python create_test_practitioner.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

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


TEST_PRACTITIONERS = [
    {
        'username': 'river.sage',
        'email': 'river.sage@example.com',
        'display_name': 'River Sage',
        'password': 'TestPass123!!',
        'business_name': 'River Sage Wellness Studio',
        'headline': 'Somatic wellness and stress reset sessions',
        'bio': 'I help clients regulate stress and restore energy through practical somatic techniques, breath pacing, and clear integration plans.',
        'modalities': 'somatic coaching, breathwork, mindfulness',
        'location': 'Portland, OR',
        'is_virtual': True,
        'years_experience': 8,
        'services': [
            {
                'category_slug': 'wellness',
                'name': 'Somatic Reset Session',
                'description': 'A body-based reset for stress relief and grounded focus with a personalized follow-up plan.',
                'duration_minutes': 60,
                'price_cents': 14500,
                'delivery_format': Service.DeliveryFormat.BOTH,
            },
            {
                'category_slug': 'wellness',
                'name': 'Breathwork Integration',
                'description': 'Guided breathwork sequence plus practical integration support for your week ahead.',
                'duration_minutes': 45,
                'price_cents': 11000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
            },
        ],
    },
    {
        'username': 'luna.ash',
        'email': 'luna.ash@example.com',
        'display_name': 'Luna Ash',
        'password': 'TestPass123!!',
        'business_name': 'Luna Ash Spiritual Care',
        'headline': 'Intuitive mentorship and ritual planning',
        'bio': 'I support life transitions with intuitive sessions that blend grounded reflection, ritual structure, and gentle accountability.',
        'modalities': 'intuitive guidance, ritual design, meditation',
        'location': 'Los Angeles, CA',
        'is_virtual': True,
        'years_experience': 10,
        'services': [
            {
                'category_slug': 'spirituality',
                'name': 'Ritual Planning Consultation',
                'description': 'Design a personalized ritual for transitions, grief, milestones, or renewed intention.',
                'duration_minutes': 75,
                'price_cents': 17500,
                'delivery_format': Service.DeliveryFormat.BOTH,
            },
            {
                'category_slug': 'spirituality',
                'name': 'Intuitive Clarity Session',
                'description': 'A focused session to clarify decisions, patterns, and practical next steps.',
                'duration_minutes': 60,
                'price_cents': 16000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
            },
        ],
    },
    {
        'username': 'mina.sol',
        'email': 'mina.sol@example.com',
        'display_name': 'Mina Sol',
        'password': 'TestPass123!!',
        'business_name': 'Mina Sol Beauty Rituals',
        'headline': 'Holistic beauty rituals with restorative care',
        'bio': 'Each appointment combines skin support, nervous-system-aware pacing, and a realistic home ritual you can maintain.',
        'modalities': 'holistic esthetics, beauty ritual, skin wellness',
        'location': 'Austin, TX',
        'is_virtual': False,
        'years_experience': 6,
        'services': [
            {
                'category_slug': 'beauty',
                'name': 'Glow Ritual Facial',
                'description': 'A restorative treatment with skin consultation, gentle exfoliation, and aftercare guidance.',
                'duration_minutes': 90,
                'price_cents': 19500,
                'delivery_format': Service.DeliveryFormat.IN_PERSON,
            },
        ],
    },
    {
        'username': 'noah.elm',
        'email': 'noah.elm@example.com',
        'display_name': 'Noah Elm',
        'password': 'TestPass123!!',
        'business_name': 'Elm Path Coaching',
        'headline': 'Career and leadership coaching for transitions',
        'bio': 'I work with founders and operators who need strategic clarity, stronger communication, and a sustainable pace.',
        'modalities': 'career coaching, leadership, communication',
        'location': 'Seattle, WA',
        'is_virtual': True,
        'years_experience': 12,
        'services': [
            {
                'category_slug': 'coaching',
                'name': 'Clarity Strategy Session',
                'description': 'Decision-focused coaching for leadership transitions and major career inflection points.',
                'duration_minutes': 60,
                'price_cents': 22000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
            },
            {
                'category_slug': 'coaching',
                'name': 'Monthly Leadership Intensive',
                'description': 'Four coaching sessions with weekly accountability, reflection prompts, and practical tools.',
                'duration_minutes': 60,
                'price_cents': 79000,
                'delivery_format': Service.DeliveryFormat.VIRTUAL,
            },
        ],
    },
]


def ensure_categories() -> None:
    for item in CATEGORIES:
        Category.objects.update_or_create(
            slug=item['slug'],
            defaults={
                'name': item['name'],
                'description': item['description'],
            },
        )


def seed_practitioner(practitioner: dict) -> None:
    user, _ = User.objects.get_or_create(
        username=practitioner['username'],
        defaults={
            'email': practitioner['email'],
            'display_name': practitioner['display_name'],
            'role': User.Role.PROFESSIONAL,
            'is_staff': False,
            'is_superuser': False,
        },
    )

    user.email = practitioner['email']
    user.display_name = practitioner['display_name']
    user.role = User.Role.PROFESSIONAL
    user.set_password(practitioner['password'])
    user.save()

    profile, _ = ProfessionalProfile.objects.get_or_create(
        user=user,
        defaults={
            'business_name': practitioner['business_name'],
            'headline': practitioner['headline'],
            'bio': practitioner['bio'],
            'modalities': practitioner['modalities'],
            'location': practitioner['location'],
            'is_virtual': practitioner['is_virtual'],
            'years_experience': practitioner['years_experience'],
            'is_visible': True,
            'is_verified': True,
            'approval_status': ProfessionalProfile.ApprovalStatus.APPROVED,
        },
    )

    profile.business_name = practitioner['business_name']
    profile.headline = practitioner['headline']
    profile.bio = practitioner['bio']
    profile.modalities = practitioner['modalities']
    profile.location = practitioner['location']
    profile.is_virtual = practitioner['is_virtual']
    profile.years_experience = practitioner['years_experience']
    profile.is_visible = True
    profile.is_verified = True
    profile.approval_status = ProfessionalProfile.ApprovalStatus.APPROVED
    profile.save()

    for service_data in practitioner['services']:
        category = Category.objects.get(slug=service_data['category_slug'])
        Service.objects.update_or_create(
            professional=profile,
            name=service_data['name'],
            defaults={
                'category': category,
                'description': service_data['description'],
                'duration_minutes': service_data['duration_minutes'],
                'price_cents': service_data['price_cents'],
                'delivery_format': service_data['delivery_format'],
                'is_active': True,
            },
        )


if __name__ == '__main__':
    ensure_categories()

    print('Seeding realistic practitioner test data...')
    for practitioner_data in TEST_PRACTITIONERS:
        seed_practitioner(practitioner_data)
        print(f"  - Seeded {practitioner_data['display_name']} ({practitioner_data['username']})")

    print('\nLogin credentials (all accounts):')
    print('  Password: TestPass123!!')
    print('  Usernames:')
    for practitioner_data in TEST_PRACTITIONERS:
        print(f"    - {practitioner_data['username']}")

    print('\nDone. Visit http://localhost:8000/ to see updated featured practitioners.')
