from django.urls import path

from .views import (
    availability_list_view,
    booking_action_view,
    booking_create_view,
    booking_guest_resume_view,
    booking_list_view,
    booking_payment_cancel_view,
    booking_payment_retry_view,
    booking_payment_success_view,
    stripe_webhook_view,
)

app_name = 'booking'

urlpatterns = [
    path('availability/', availability_list_view, name='availability'),
    path('bookings/', booking_list_view, name='list'),
    path('bookings/<int:booking_id>/<str:action>/', booking_action_view, name='action'),
    path('bookings/payment/success/', booking_payment_success_view, name='payment_success'),
    path('bookings/payment/cancel/', booking_payment_cancel_view, name='payment_cancel'),
    path('bookings/payment/<int:intent_id>/retry/', booking_payment_retry_view, name='payment_retry'),
    path('bookings/guest/resume/', booking_guest_resume_view, name='guest_resume'),
    path('payments/webhook/stripe/', stripe_webhook_view, name='stripe_webhook'),
    path('services/<int:service_id>/book/', booking_create_view, name='create'),
]
