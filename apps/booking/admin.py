from django.contrib import admin

from .models import AvailabilityWindow, Booking


@admin.register(AvailabilityWindow)
class AvailabilityWindowAdmin(admin.ModelAdmin):
	list_display = ('professional', 'weekday', 'start_time', 'end_time', 'is_active')
	list_filter = ('weekday', 'is_active')


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
	list_display = ('service', 'client', 'professional', 'start_at', 'status')
	list_filter = ('status',)
	search_fields = ('service__name', 'client__username', 'professional__business_name')
