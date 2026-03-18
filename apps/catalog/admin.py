from django.contrib import admin

from .models import AnalyticsEvent, Category, Service


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name', 'slug')
	search_fields = ('name',)
	prepopulated_fields = {'slug': ('name',)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
	list_display = ('name', 'professional', 'category', 'duration_minutes', 'price_cents', 'is_active')
	list_filter = ('category', 'delivery_format', 'is_active')
	search_fields = ('name', 'professional__business_name')


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
	list_display = ('name', 'source', 'path', 'profile_id', 'user', 'created_at')
	list_filter = ('name', 'source', 'created_at')
	search_fields = ('path', 'name', 'source', 'user__username')
