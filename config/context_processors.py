from django.conf import settings


def analytics(request):
    """Expose analytics settings to all templates."""
    return {
        'analytics_ga4_measurement_id': getattr(settings, 'ANALYTICS_GA4_MEASUREMENT_ID', ''),
        'analytics_plausible_domain': getattr(settings, 'ANALYTICS_PLAUSIBLE_DOMAIN', ''),
        'analytics_plausible_script_url': getattr(
            settings,
            'ANALYTICS_PLAUSIBLE_SCRIPT_URL',
            'https://plausible.io/js/script.js',
        ),
    }
