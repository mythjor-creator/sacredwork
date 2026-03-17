from django.urls import path

from .views import onboarding_view, profile_edit_view

app_name = 'professionals'

urlpatterns = [
    path('onboarding/', onboarding_view, name='onboarding'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
]
