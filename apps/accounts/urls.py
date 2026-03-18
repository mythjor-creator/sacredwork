from django.contrib.auth.views import LogoutView
from django.urls import path

from .views import ClairbookLoginView, account_settings_view, dashboard_view, signup_view

app_name = 'accounts'

urlpatterns = [
    path('dashboard/', dashboard_view, name='dashboard'),
    path('settings/', account_settings_view, name='settings'),
    path('signup/', signup_view, name='signup'),
    path('login/', ClairbookLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
