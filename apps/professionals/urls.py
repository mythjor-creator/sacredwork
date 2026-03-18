from django.urls import path

from .views import (
    onboarding_view,
    profile_core_view,
    profile_credentials_view,
    profile_edit_view,
    profile_gallery_view,
)

app_name = 'professionals'

urlpatterns = [
    path('onboarding/', onboarding_view, name='onboarding'),
    path('profile/core/', profile_core_view, name='profile_core'),
    path('profile/gallery/', profile_gallery_view, name='profile_gallery'),
    path('profile/credentials/', profile_credentials_view, name='profile_credentials'),
    path('profile/edit/', profile_edit_view, name='profile_edit'),
]
