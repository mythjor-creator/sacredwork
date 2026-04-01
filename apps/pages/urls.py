from django.urls import path
from . import views

app_name = 'pages'

urlpatterns = [
    path('', views.landing_view, name='landing'),
    path('health/', views.healthcheck_view, name='healthcheck'),
    path('style-sheet/', views.style_sheet_view, name='style_sheet'),
    path('about/', views.about_view, name='about'),
    path('pricing/', views.pricing_view, name='pricing'),
    path('privacy/', views.privacy_view, name='privacy'),
    path('terms/', views.terms_view, name='terms'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('account/export-data/', views.gdpr_export_view, name='gdpr_export'),
    path('account/delete/', views.gdpr_delete_view, name='gdpr_delete'),
    path('admin/gdpr-audit/', views.admin_gdpr_audit_view, name='admin_gdpr_audit'),
]
