# Sacred Work App

A Django marketplace MVP for discovering and booking professionals in holistic wellness, beauty, spirituality, and coaching.

## Current Implementation

- Custom user model with account roles (client, professional, admin)
- Professional profiles for coach/provider onboarding
- Service catalog with categories and delivery formats
- Booking and recurring availability data models
- Moderation decision model for profile/service review
- Django admin setup for all core domain entities

## Local Setup

1. Create and activate a virtual environment:

   ```bash
   /usr/local/bin/python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run migrations:

   ```bash
   python manage.py migrate
   ```

4. Create an admin user:

   ```bash
   python manage.py createsuperuser
   ```

5. Start the development server:

   ```bash
   python manage.py runserver
   ```

Then open http://127.0.0.1:8000/admin

## Next Build Targets

- Professional onboarding forms and role-aware auth flow
- Marketplace search and profile detail pages
- Time slot generation and booking workflow logic
- Email notifications for booking lifecycle events
# trigger deploy
