#!/usr/bin/env python
"""
Quick script to create a test practitioner account for development.
Usage: python create_test_practitioner.py
"""
import os
import django
from django.contrib.auth import get_user_model

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.accounts.models import User
from apps.professionals.models import ProfessionalProfile

# Create or update test practitioner
user, created = User.objects.get_or_create(
    username='test_practitioner',
    defaults={
        'email': 'practitioner@example.com',
        'role': User.Role.PROFESSIONAL,
        'is_staff': False,
        'is_superuser': False,
    }
)

if created:
    user.set_password('TestPass123!!')
    user.save()
    print(f"✅ Created user: {user.username}")
else:
    print(f"✓ User already exists: {user.username}")
    user.set_password('TestPass123!!')
    user.save()

# Create professional profile if it doesn't exist
profile, created = ProfessionalProfile.objects.get_or_create(
    user=user,
    defaults={
        'headline': 'Test Practitioner',
        'bio': 'This is a test practitioner account.',
        'modalities': 'reiki, meditation',
        'years_experience': 5,
        'is_visible': True,
        'approval_status': ProfessionalProfile.ApprovalStatus.APPROVED,
    }
)

if created:
    print(f"✅ Created professional profile")
else:
    print(f"✓ Professional profile already exists")

print("\n🔐 Login credentials:")
print(f"  Username: test_practitioner")
print(f"  Password: TestPass123!!")
print("\n📍 Profile URL: http://localhost:8000/professionals/profile/edit/")
