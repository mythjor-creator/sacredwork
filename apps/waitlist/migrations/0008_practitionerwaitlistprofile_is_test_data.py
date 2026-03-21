from django.db import migrations, models


def mark_existing_test_waitlist_profiles(apps, schema_editor):
    PractitionerWaitlistProfile = apps.get_model('waitlist', 'PractitionerWaitlistProfile')
    domains = ('@example.com', '@example.org', '@example.net', '@mailinator.com')
    for profile in PractitionerWaitlistProfile.objects.all():
        email = (profile.email or '').strip().lower()
        if email.endswith(domains):
            profile.is_test_data = True
            profile.save(update_fields=['is_test_data'])


def unmark_existing_test_waitlist_profiles(apps, schema_editor):
    PractitionerWaitlistProfile = apps.get_model('waitlist', 'PractitionerWaitlistProfile')
    PractitionerWaitlistProfile.objects.filter(is_test_data=True).update(is_test_data=False)


class Migration(migrations.Migration):

    dependencies = [
        ('waitlist', '0007_founding_member_flag'),
    ]

    operations = [
        migrations.AddField(
            model_name='practitionerwaitlistprofile',
            name='is_test_data',
            field=models.BooleanField(db_index=True, default=False, help_text='Marks internal, demo, seeded, or QA signups so they can be separated from real submissions.'),
        ),
        migrations.RunPython(mark_existing_test_waitlist_profiles, unmark_existing_test_waitlist_profiles),
    ]