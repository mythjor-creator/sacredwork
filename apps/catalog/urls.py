from django.urls import path

from .views import (
    home_view,
    marketplace_view,
    professional_detail_view,
    service_create_view,
    service_edit_view,
    service_list_view,
)

app_name = 'catalog'

urlpatterns = [
    path('', home_view, name='home'),
    path('browse/', marketplace_view, name='marketplace'),
    path('professionals/<int:pk>/', professional_detail_view, name='professional_detail'),
    path('services/', service_list_view, name='service_list'),
    path('services/new/', service_create_view, name='service_create'),
    path('services/<int:pk>/edit/', service_edit_view, name='service_edit'),
]
