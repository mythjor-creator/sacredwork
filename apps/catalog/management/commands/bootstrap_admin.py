from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    help = 'Creates or updates a Django superuser from environment variables.'

    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('BOOTSTRAP_ADMIN_USERNAME')
        email = os.environ.get('BOOTSTRAP_ADMIN_EMAIL')
        password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD')

        if not (username and email and password):
            self.stderr.write(self.style.ERROR('Missing BOOTSTRAP_ADMIN_USERNAME, BOOTSTRAP_ADMIN_EMAIL, or BOOTSTRAP_ADMIN_PASSWORD env vars.'))
            return

        user, created = User.objects.get_or_create(username=username, defaults={'email': email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        if created:
            self.stdout.write(self.style.SUCCESS(f'Superuser {username} created.'))
        else:
            self.stdout.write(self.style.WARNING(f'Superuser {username} updated/reset.'))
