from django.urls import path

from .views import (
    billing_checkout_cancel_view,
    billing_checkout_start_view,
    billing_checkout_success_view,
    billing_overview_view,
    stripe_billing_webhook_view,
)

app_name = 'billing'

urlpatterns = [
    path('', billing_overview_view, name='overview'),
    path('checkout/start/', billing_checkout_start_view, name='checkout_start'),
    path('checkout/success/', billing_checkout_success_view, name='checkout_success'),
    path('checkout/cancel/', billing_checkout_cancel_view, name='checkout_cancel'),
    path('webhook/stripe/', stripe_billing_webhook_view, name='stripe_webhook'),
]
