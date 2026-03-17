from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('waitlist', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='practitionerwaitlistprofile',
            name='offers_in_person',
            field=models.BooleanField(default=False),
        ),
    ]
