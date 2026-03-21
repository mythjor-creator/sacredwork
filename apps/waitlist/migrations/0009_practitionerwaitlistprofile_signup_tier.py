from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waitlist', '0008_practitionerwaitlistprofile_is_test_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='practitionerwaitlistprofile',
            name='signup_tier',
            field=models.CharField(
                choices=[
                    ('free', 'Free Waitlist'),
                    ('basic', 'Basic Practitioner'),
                    ('featured', 'Featured'),
                    ('founding', 'Founding'),
                ],
                db_index=True,
                default='free',
                help_text='Selected signup flow from pricing and waitlist entry points.',
                max_length=20,
            ),
        ),
    ]
