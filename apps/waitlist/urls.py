from django.urls import path
from .views import waitlist_landing_view, simple_waitlist_signup

app_name = 'waitlist'

urlpatterns = [
    path('', waitlist_landing_view, name='landing'),
    path('signup/', simple_waitlist_signup, name='simple_signup'),
]
