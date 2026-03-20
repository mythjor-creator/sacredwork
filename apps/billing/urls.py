from django.urls import path

from .views import billing_overview_view

app_name = 'billing'

urlpatterns = [
    path('', billing_overview_view, name='overview'),
]
