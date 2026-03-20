from django.db import migrations


def seed_founding_plan(apps, schema_editor):
    SubscriptionPlan = apps.get_model('billing', 'SubscriptionPlan')
    SubscriptionPlan.objects.update_or_create(
        code='founding-annual',
        defaults={
            'name': 'Founding Practitioner Annual',
            'amount_cents': 7900,
            'billing_interval': 'year',
            'founding_only': True,
            'is_active': True,
            'display_order': 0,
        },
    )


def unseed_founding_plan(apps, schema_editor):
    SubscriptionPlan = apps.get_model('billing', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(code='founding-annual').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_founding_plan, unseed_founding_plan),
    ]