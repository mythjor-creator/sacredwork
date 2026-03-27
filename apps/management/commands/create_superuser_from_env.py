import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Create a superuser from SUPERUSER_USERNAME, SUPERUSER_EMAIL, and SUPERUSER_PASSWORD environment variables.'

    def handle(self, *args, **options):
        User = get_user_model()

        username = os.environ.get('SUPERUSER_USERNAME')
        email = os.environ.get('SUPERUSER_EMAIL', '')
        password = os.environ.get('SUPERUSER_PASSWORD')

        if not username:
            raise CommandError('SUPERUSER_USERNAME environment variable is not set.')
        if not password:
            raise CommandError('SUPERUSER_PASSWORD environment variable is not set.')

        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'Superuser "{username}" already exists — skipping creation.')
            )
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(
            self.style.SUCCESS(f'Superuser "{username}" created successfully.')
        )
