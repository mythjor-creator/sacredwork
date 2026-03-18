from django.contrib import admin

from .models import AnalyticsEvent, Category, Service, ServiceTier


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


@admin.register(ServiceTier)
class ServiceTierAdmin(admin.ModelAdmin):
	list_display = ('service', 'name', 'price_cents', 'duration_minutes', 'sort_order', 'is_active')
	list_filter = ('is_active',)
	search_fields = ('service__name', 'service__professional__business_name', 'name')


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
	list_display = ('name', 'source', 'path', 'profile_id', 'user', 'created_at')
	list_filter = ('name', 'source', 'created_at')
	search_fields = ('path', 'name', 'source', 'user__username')
