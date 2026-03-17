from django.urls import path

from .views import availability_list_view, booking_action_view, booking_create_view, booking_list_view

app_name = 'booking'

urlpatterns = [
    path('availability/', availability_list_view, name='availability'),
    path('bookings/', booking_list_view, name='list'),
    path('bookings/<int:booking_id>/<str:action>/', booking_action_view, name='action'),
    path('services/<int:service_id>/book/', booking_create_view, name='create'),
]
