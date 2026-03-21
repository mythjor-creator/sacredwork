from django.db import migrations, models


def mark_existing_test_accounts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    domains = ('@example.com', '@example.org', '@example.net', '@mailinator.com')
    for user in User.objects.all():
        email = (user.email or '').strip().lower()
        if email.endswith(domains):
            user.is_test_account = True
            user.save(update_fields=['is_test_account'])


def unmark_existing_test_accounts(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    User.objects.filter(is_test_account=True).update(is_test_account=False)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_test_account',
            field=models.BooleanField(db_index=True, default=False, help_text='Marks internal, demo, seeded, or QA accounts so they can be separated from real users.'),
        ),
        migrations.RunPython(mark_existing_test_accounts, unmark_existing_test_accounts),
    ]