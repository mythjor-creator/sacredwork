from django.urls import path

from .views import moderation_queue_view, moderation_decide_view

app_name = 'moderation'

urlpatterns = [
    path('queue/', moderation_queue_view, name='queue'),
    path('queue/<int:profile_id>/decide/', moderation_decide_view, name='decide'),
]
