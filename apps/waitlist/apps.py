from django.apps import AppConfig


class WaitlistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.waitlist'
    verbose_name = 'Waitlist'

    def ready(self):
        from django.contrib import admin
        _orig = admin.AdminSite.get_app_list

        def _waitlist_first(self_site, request, app_label=None):
            app_list = _orig(self_site, request, app_label=app_label)
            priority = [a for a in app_list if a['app_label'] == 'waitlist']
            others = [a for a in app_list if a['app_label'] != 'waitlist']
            return priority + others

        admin.AdminSite.get_app_list = _waitlist_first
