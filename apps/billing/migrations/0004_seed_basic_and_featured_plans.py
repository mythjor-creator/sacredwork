from django.db import migrations


def seed_practitioner_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('billing', 'SubscriptionPlan')

    SubscriptionPlan.objects.update_or_create(
        code='basic-monthly',
        defaults={
            'name': 'Basic Practitioner Monthly',
            'amount_cents': 999,
            'billing_interval': 'month',
            'founding_only': False,
            'is_active': True,
            'display_order': 0,
        },
    )
    SubscriptionPlan.objects.update_or_create(
        code='featured-monthly',
        defaults={
            'name': 'Featured Practitioner Monthly',
            'amount_cents': 2499,
            'billing_interval': 'month',
            'founding_only': False,
            'is_active': True,
            'display_order': 1,
        },
    )
    SubscriptionPlan.objects.update_or_create(
        code='founding-annual',
        defaults={
            'name': 'Founding Practitioner Annual',
            'amount_cents': 7900,
            'billing_interval': 'year',
            'founding_only': True,
            'is_active': True,
            'display_order': 2,
        },
    )


def unseed_practitioner_plans(apps, schema_editor):
    SubscriptionPlan = apps.get_model('billing', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(code__in=['basic-monthly', 'featured-monthly']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0003_billingwebhookevent'),
    ]

    operations = [
        migrations.RunPython(seed_practitioner_plans, unseed_practitioner_plans),
    ]