from django.urls import path

from .views import waitlist_landing_view

app_name = 'waitlist'

urlpatterns = [
    path('', waitlist_landing_view, name='landing'),
]
